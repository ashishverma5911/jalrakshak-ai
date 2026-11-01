"""
Scientific GeoTIFF Raster Decoder for JalRakshak AI.
Performs pure-Python binary decoding of georeferenced GeoTIFF rasters into NumPy arrays.
Extracts ModelPixelScale, ModelTiepoint, GeoKeyDirectory CRS, GDAL_NODATA, and geotransform.
Enforces strict dimension and memory safety bounds before allocating pixel arrays.

Safety Limits (Configurable):
- MAX_RASTER_WIDTH: 10,000 pixels
- MAX_RASTER_HEIGHT: 10,000 pixels
- MAX_RASTER_PIXELS: 25,000,000 pixels
- MAX_RASTER_BANDS: 4
- Maximum decoded memory: strictly bounded to prevent heap exhaustion on 512 MB hosting.
"""

import struct
import zlib
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("jalrakshak.pipeline.raster")

# Configurable Safety Limits
MAX_RASTER_WIDTH = 10000
MAX_RASTER_HEIGHT = 10000
MAX_RASTER_PIXELS = 25_000_000
MAX_RASTER_BANDS = 4

# Known TIFF magic numbers
MAGIC_TIFF_LE = b"II\x2a\x00"
MAGIC_TIFF_BE = b"MM\x00\x2a"
MAGIC_BIGTIFF_LE = b"II\x2b\x00"
MAGIC_BIGTIFF_BE = b"MM\x00\x2b"


class RasterDecodingError(ValueError):
    """Raised when raster validation or decoding fails."""
    pass


@dataclass
class GeoTIFFDecodedResult:
    is_valid: bool
    scientific_decoding_status: str  # "SUCCESS", "FAILED", "MALFORMED"
    width: int = 0
    height: int = 0
    bands: int = 1
    bits_per_sample: int = 32
    compression: int = 1
    crs: str = "EPSG:4326"
    geotransform: Optional[Tuple[float, float, float, float, float, float]] = None
    bounding_box: Optional[Dict[str, float]] = None  # min_lng, min_lat, max_lng, max_lat
    pixel_scale: Optional[Tuple[float, float]] = None
    tiepoint_origin: Optional[Tuple[float, float]] = None
    nodata_value: Optional[float] = None
    total_records: int = 0
    valid_records: int = 0
    missing_records: int = 0
    extreme_records: int = 0
    mean_value: Optional[float] = None
    max_value: Optional[float] = None
    min_value: Optional[float] = None
    raster_array: Optional[np.ndarray] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class GeoTIFFDecoder:
    """
    Decodes georeferenced GeoTIFF datasets into NumPy pixel arrays and coordinate matrices.
    """

    @classmethod
    def decode_geotiff(cls, file_bytes: bytes) -> GeoTIFFDecodedResult:
        """
        Parses and decodes GeoTIFF binary structure, extracts georeferencing,
        validates dimension bounds, and decodes raster pixel data.
        """
        if len(file_bytes) < 8:
            return GeoTIFFDecodedResult(
                is_valid=False,
                scientific_decoding_status="FAILED",
                errors=["File size too small for a valid TIFF header."],
            )

        # 1. Determine Endianness
        byte_order = file_bytes[:2]
        if byte_order == b"II":
            endian = "<"
        elif byte_order == b"MM":
            endian = ">"
        else:
            return GeoTIFFDecodedResult(
                is_valid=False,
                scientific_decoding_status="FAILED",
                errors=["Invalid TIFF byte order indicator (expected 'II' or 'MM')."],
            )

        # 2. Check Magic Number
        magic = struct.unpack(f"{endian}H", file_bytes[2:4])[0]
        if magic != 42 and magic != 43:
            return GeoTIFFDecodedResult(
                is_valid=False,
                scientific_decoding_status="FAILED",
                errors=[f"Invalid TIFF magic number: {magic} (expected 42 or 43)."],
            )

        # BigTIFF vs Classic TIFF
        is_bigtiff = (magic == 43)
        if is_bigtiff:
            if len(file_bytes) < 16:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="FAILED",
                    errors=["BigTIFF header truncated."],
                )
            ifd_offset = struct.unpack(f"{endian}Q", file_bytes[8:16])[0]
        else:
            ifd_offset = struct.unpack(f"{endian}I", file_bytes[4:8])[0]

        if ifd_offset >= len(file_bytes) or ifd_offset < 8:
            return GeoTIFFDecodedResult(
                is_valid=False,
                scientific_decoding_status="FAILED",
                errors=[f"Corrupt TIFF: IFD offset {ifd_offset} outside file boundaries."],
            )

        # 3. Read IFD Entries
        try:
            if is_bigtiff:
                num_entries = struct.unpack(f"{endian}Q", file_bytes[ifd_offset : ifd_offset + 8])[0]
                entry_size = 20
                entries_offset = ifd_offset + 8
            else:
                num_entries = struct.unpack(f"{endian}H", file_bytes[ifd_offset : ifd_offset + 2])[0]
                entry_size = 12
                entries_offset = ifd_offset + 2

            tags: Dict[int, Tuple[int, int, int]] = {}  # tag -> (field_type, count, val_or_offset)

            for i in range(min(num_entries, 256)):
                e_start = entries_offset + (i * entry_size)
                if e_start + entry_size > len(file_bytes):
                    break
                if is_bigtiff:
                    tag, ftype, count, val_or_offset = struct.unpack(f"{endian}HHQQ", file_bytes[e_start : e_start + 20])
                else:
                    tag, ftype, count, val_or_offset = struct.unpack(f"{endian}HHII", file_bytes[e_start : e_start + 12])
                tags[tag] = (ftype, count, val_or_offset)

            def get_tag_value(tag_id: int, default: Any = None) -> Any:
                if tag_id not in tags:
                    return default
                ftype, count, val_or_offset = tags[tag_id]
                # Type sizes: 1=BYTE, 2=ASCII, 3=SHORT(2), 4=LONG(4), 5=RATIONAL(8), 12=DOUBLE(8)
                type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 8: 2, 9: 4, 11: 4, 12: 8}
                tsize = type_sizes.get(ftype, 1)
                total_bytes = count * tsize

                if total_bytes <= (8 if is_bigtiff else 4):
                    return val_or_offset
                else:
                    # Offset into file
                    offset = val_or_offset
                    if offset + total_bytes > len(file_bytes):
                        return default
                    return offset

            # 4. Extract Essential Image Dimensions
            width = get_tag_value(256, 0)
            height = get_tag_value(257, 0)
            bits_per_sample = get_tag_value(258, 32)
            compression = get_tag_value(259, 1)  # 1 = uncompressed, 8 = Deflate
            samples_per_pixel = get_tag_value(277, 1)
            sample_format = get_tag_value(339, 1)  # 1=uint, 2=int, 3=float

            # 5. Enforce Configurable Safety Limits BEFORE Allocation
            errors = []
            warnings = []

            if not isinstance(width, int) or width <= 0 or not isinstance(height, int) or height <= 0:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="MALFORMED",
                    errors=[f"Invalid or corrupt raster dimensions: {width} × {height}."],
                )

            if width > MAX_RASTER_WIDTH or height > MAX_RASTER_HEIGHT:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="MALFORMED",
                    width=width,
                    height=height,
                    errors=[
                        f"Raster dimensions ({width} × {height}) exceed configured maximum safety limits "
                        f"({MAX_RASTER_WIDTH} × {MAX_RASTER_HEIGHT}). Allocation halted to prevent heap exhaustion."
                    ],
                )

            total_pixels = width * height
            if total_pixels > MAX_RASTER_PIXELS:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="MALFORMED",
                    width=width,
                    height=height,
                    errors=[
                        f"Total raster pixel count ({total_pixels:,}) exceeds maximum safety budget of {MAX_RASTER_PIXELS:,} pixels."
                    ],
                )

            if samples_per_pixel > MAX_RASTER_BANDS:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="MALFORMED",
                    width=width,
                    height=height,
                    bands=samples_per_pixel,
                    errors=[
                        f"Raster band count ({samples_per_pixel}) exceeds supported maximum of {MAX_RASTER_BANDS} bands."
                    ],
                )

            # 6. Extract Georeferencing (PixelScale, Tiepoint, GeoKeys)
            has_pixel_scale = 33550 in tags
            has_tiepoint = 33922 in tags
            has_geokeys = 34735 in tags

            if not (has_pixel_scale and has_tiepoint):
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="FAILED",
                    width=width,
                    height=height,
                    errors=[
                        "Missing mandatory GeoTIFF spatial tags: ModelPixelScaleTag (33550) and "
                        "ModelTiepointTag (33922) are required for scientific spatial referencing."
                    ],
                )

            # Read ModelPixelScale (Double[3]: ScaleX, ScaleY, ScaleZ)
            ps_offset = get_tag_value(33550)
            if not isinstance(ps_offset, int) or ps_offset + 24 > len(file_bytes):
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="FAILED",
                    errors=["ModelPixelScaleTag offset is out of file bounds."],
                )
            pixel_scale = struct.unpack(f"{endian}3d", file_bytes[ps_offset : ps_offset + 24])
            scale_x, scale_y = float(pixel_scale[0]), float(pixel_scale[1])

            # Read ModelTiepoint (Double[6]: I, J, K, X, Y, Z)
            tp_offset = get_tag_value(33922)
            if not isinstance(tp_offset, int) or tp_offset + 48 > len(file_bytes):
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="FAILED",
                    errors=["ModelTiepointTag offset is out of file bounds."],
                )
            tiepoints = struct.unpack(f"{endian}6d", file_bytes[tp_offset : tp_offset + 48])
            origin_x, origin_y = float(tiepoints[3]), float(tiepoints[4])

            # Compute Geotransform and Bounding Box
            geotransform = (origin_x, scale_x, 0.0, origin_y, 0.0, -scale_y)
            min_lng = origin_x
            max_lng = origin_x + (width * scale_x)
            max_lat = origin_y
            min_lat = origin_y - (height * scale_y)

            # Coordinate range check
            if min_lng < -180.0 or max_lng > 360.0 or min_lat < -90.0 or max_lat > 90.0:
                warnings.append(
                    f"Raster geographic bounds [{min_lng:.4f}, {min_lat:.4f}, {max_lng:.4f}, {max_lat:.4f}] "
                    "appear to be projected coordinates rather than WGS84 degrees."
                )

            bounding_box = {
                "min_lng": round(min_lng, 6),
                "min_lat": round(min_lat, 6),
                "max_lng": round(max_lng, 6),
                "max_lat": round(max_lat, 6),
            }

            # 7. Extract CRS from GeoKeyDirectoryTag (34735)
            crs = "EPSG:4326"
            if has_geokeys:
                gk_offset = get_tag_value(34735)
                if isinstance(gk_offset, int) and gk_offset + 8 <= len(file_bytes):
                    gk_hdr = struct.unpack(f"{endian}4H", file_bytes[gk_offset : gk_offset + 8])
                    num_keys = gk_hdr[3]
                    for k in range(num_keys):
                        k_off = gk_offset + 8 + (k * 8)
                        if k_off + 8 <= len(file_bytes):
                            kid, loc, cnt, val = struct.unpack(f"{endian}4H", file_bytes[k_off : k_off + 8])
                            if kid in [2048, 3072] and loc == 0:
                                crs = f"EPSG:{val}"
                                break

            # 8. Extract GDAL_NODATA (42113)
            nodata_val = None
            if 42113 in tags:
                nd_offset = get_tag_value(42113)
                nd_cnt = tags[42113][1]
                if isinstance(nd_offset, int) and nd_offset + nd_cnt <= len(file_bytes):
                    nd_str = file_bytes[nd_offset : nd_offset + nd_cnt].decode("ascii", errors="ignore").strip("\x00 \r\n")
                    try:
                        nodata_val = float(nd_str)
                    except ValueError:
                        pass

            # 9. Decode Raster Pixel Strips
            if compression not in [1, 8]:  # 1 = None, 8 = Deflate
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="UNSUPPORTED",
                    width=width,
                    height=height,
                    crs=crs,
                    geotransform=geotransform,
                    bounding_box=bounding_box,
                    errors=[f"Unsupported TIFF compression method ({compression}). Only uncompressed (1) and Deflate (8) are supported."],
                )

            strip_offsets_raw = get_tag_value(273)
            strip_bytes_raw = get_tag_value(279)

            if strip_offsets_raw is None or strip_bytes_raw is None:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="FAILED",
                    errors=["Missing StripOffsets (273) or StripByteCounts (279) tags."],
                )

            # Determine dtype
            if bits_per_sample == 32 and sample_format == 3:
                dtype = np.float32
            elif bits_per_sample == 64 and sample_format == 3:
                dtype = np.float64
            elif bits_per_sample == 16 and sample_format == 1:
                dtype = np.uint16
            elif bits_per_sample == 16 and sample_format == 2:
                dtype = np.int16
            elif bits_per_sample == 32 and sample_format == 1:
                dtype = np.uint32
            elif bits_per_sample == 8:
                dtype = np.uint8
            else:
                dtype = np.float32

            # Extract pixel bytes from strips
            strip_count = tags[273][1]
            if strip_count == 1:
                s_off = strip_offsets_raw
                s_len = strip_bytes_raw
                if s_off + s_len > len(file_bytes):
                    return GeoTIFFDecodedResult(
                        is_valid=False,
                        scientific_decoding_status="MALFORMED",
                        errors=["Strip offset and byte count point outside file boundaries."],
                    )
                raw_strip = file_bytes[s_off : s_off + s_len]
                if compression == 8:
                    try:
                        decomp_bytes = zlib.decompress(raw_strip)
                    except Exception as ze:
                        return GeoTIFFDecodedResult(
                            is_valid=False,
                            scientific_decoding_status="FAILED",
                            errors=[f"Deflate decompression error: {ze}"],
                        )
                else:
                    decomp_bytes = raw_strip
            else:
                # Multiple strips
                type_sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 8: 2, 9: 4, 11: 4, 12: 8}
                o_tsize = type_sizes.get(tags[273][0], 4)
                b_tsize = type_sizes.get(tags[279][0], 4)
                o_offset = strip_offsets_raw
                b_offset = strip_bytes_raw

                decomp_parts = []
                fmt_o = "I" if o_tsize == 4 else "H"
                fmt_b = "I" if b_tsize == 4 else "H"

                for si in range(strip_count):
                    s_off = struct.unpack_from(f"{endian}{fmt_o}", file_bytes, o_offset + (si * o_tsize))[0]
                    s_len = struct.unpack_from(f"{endian}{fmt_b}", file_bytes, b_offset + (si * b_tsize))[0]
                    if s_off + s_len > len(file_bytes):
                        break
                    part = file_bytes[s_off : s_off + s_len]
                    if compression == 8:
                        part = zlib.decompress(part)
                    decomp_parts.append(part)
                decomp_bytes = b"".join(decomp_parts)

            # Unpack into NumPy array
            try:
                expected_bytes = total_pixels * np.dtype(dtype).itemsize
                if len(decomp_bytes) < expected_bytes:
                    decomp_bytes = decomp_bytes.ljust(expected_bytes, b"\x00")
                elif len(decomp_bytes) > expected_bytes:
                    decomp_bytes = decomp_bytes[:expected_bytes]

                arr = np.frombuffer(decomp_bytes, dtype=dtype).reshape((height, width))
                raster_float = arr.astype(np.float32)

                # Mask NoData and NaNs
                invalid_mask = np.isnan(raster_float) | np.isinf(raster_float)
                if nodata_val is not None:
                    invalid_mask = invalid_mask | (raster_float == nodata_val)
                # Standard negative missing indicators
                invalid_mask = invalid_mask | (raster_float <= -900.0)

                valid_mask = ~invalid_mask
                valid_data = raster_float[valid_mask]

                valid_records = int(valid_data.size)
                missing_records = int(np.sum(invalid_mask))

                # Check negative values
                if valid_records > 0:
                    neg_cnt = int(np.sum(valid_data < 0.0))
                    if neg_cnt > 0:
                        return GeoTIFFDecodedResult(
                            is_valid=False,
                            scientific_decoding_status="FAILED",
                            width=width,
                            height=height,
                            crs=crs,
                            geotransform=geotransform,
                            bounding_box=bounding_box,
                            errors=[
                                f"Physically impossible negative precipitation detected ({neg_cnt} pixels < 0.0 mm)."
                            ],
                        )

                extreme_records = int(np.sum(valid_data > 500.0)) if valid_records > 0 else 0
                if extreme_records > 0:
                    warnings.append(
                        f"Raster contains {extreme_records} provisional extreme pixels exceeding 500 mm threshold."
                    )

                mean_val = round(float(np.mean(valid_data)), 2) if valid_records > 0 else None
                max_val = round(float(np.max(valid_data)), 2) if valid_records > 0 else None
                min_val = round(float(np.min(valid_data)), 2) if valid_records > 0 else None

                return GeoTIFFDecodedResult(
                    is_valid=True,
                    scientific_decoding_status="SUCCESS",
                    width=width,
                    height=height,
                    bands=samples_per_pixel,
                    bits_per_sample=bits_per_sample,
                    compression=compression,
                    crs=crs,
                    geotransform=geotransform,
                    bounding_box=bounding_box,
                    pixel_scale=(scale_x, scale_y),
                    tiepoint_origin=(origin_x, origin_y),
                    nodata_value=nodata_val,
                    total_records=total_pixels,
                    valid_records=valid_records,
                    missing_records=missing_records,
                    extreme_records=extreme_records,
                    mean_value=mean_val,
                    max_value=max_val,
                    min_value=min_val,
                    raster_array=raster_float,
                    warnings=warnings,
                    errors=errors,
                )

            except Exception as e:
                return GeoTIFFDecodedResult(
                    is_valid=False,
                    scientific_decoding_status="FAILED",
                    width=width,
                    height=height,
                    crs=crs,
                    geotransform=geotransform,
                    bounding_box=bounding_box,
                    errors=[f"Failed to assemble raster array: {e}"],
                )

        except Exception as e:
            logger.error(f"GeoTIFF decoding failed: {e}", exc_info=True)
            return GeoTIFFDecodedResult(
                is_valid=False,
                scientific_decoding_status="FAILED",
                errors=[f"GeoTIFF structure parsing error: {e}"],
            )
