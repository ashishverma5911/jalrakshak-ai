import React, { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  PhoneCall,
  ExternalLink,
  Flame,
  Waves,
  Heart,
  FileText,
  Copy,
  Check,
  Search,
  Info,
  ShieldAlert,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { Card } from '../components/common/Card';

const CONTACTS_DATA = [
  {
    title: 'UP Relief Commissioner (State Control Room)',
    phone: '1070',
    fullPhone: '0522-2238084',
    role: 'State Emergency Operation Centre (Lucknow) — 24x7 Operations',
    website: 'rahat.up.nic.in',
    category: 'Statewide',
    type: 'Official Emergency Authority',
  },
  {
    title: 'Gorakhpur District Magistrate Control Room',
    phone: '1077',
    fullPhone: '0551-2201796',
    role: 'District Disaster Management Authority (Gorakhpur Flood Operations)',
    website: 'gorakhpur.nic.in',
    category: 'Gorakhpur',
    type: 'District Emergency Operations',
  },
  {
    title: 'Mahoba District Emergency Helpline',
    phone: '1077',
    fullPhone: '05281-254427',
    role: 'District Drought Mitigation & Water Tanker Dispatch Control',
    website: 'mahoba.nic.in',
    category: 'Mahoba',
    type: 'District Emergency Operations',
  },
  {
    title: 'NDRF 11th Battalion (Varanasi / Eastern UP)',
    phone: '0542-2624467',
    fullPhone: '0542-2624467',
    role: 'National Disaster Response Force (Eastern UP & Rapti Basin Relief)',
    website: 'ndrf.gov.in',
    category: 'Rescue',
    type: 'Central Search & Rescue',
  },
  {
    title: 'IMD Lucknow Regional Meteorological Centre',
    phone: '0522-2435404',
    fullPhone: '0522-2435404',
    role: 'Official Weather Forecasts & Doppler Weather Radar Bulletins',
    website: 'mausam.imd.gov.in/lucknow',
    category: 'Weather',
    type: 'National Meteorological Agency',
  },
  {
    title: 'Central Water Commission (CWC Flood Unit)',
    phone: '011-29583200',
    fullPhone: '011-29583200',
    role: 'Middle Ganga / Rapti Basin River Gauge Stages & Danger-Mark Bulletins',
    website: 'ffs.india-water.gov.in',
    category: 'River Stage',
    type: 'Official River Gauge Authority',
  },
];

const OFFICIAL_RESOURCES = [
  {
    title: 'UP State Disaster Management Authority (UPSDMA)',
    role: 'Official Flood & Disaster Action Bulletins and SOPs',
    desc: 'Authoritative state government portal for disaster guidelines, district hazard zoning, and relief standard operating procedures.',
    url: 'https://upsdma.up.nic.in',
    type: 'Official Advisory Reference Link',
  },
  {
    title: 'Central Water Commission (CWC) Flood Forecast Portal',
    role: 'Official River Gauge Heights & Inundation Advisories',
    desc: 'Official real-time river stage telemetry, danger-mark hydrographs, and flood warning levels across India.',
    url: 'https://ffs.india-water.gov.in',
    type: 'Official Advisory Reference Link',
  },
  {
    title: 'IMD Regional Meteorological Centre, Lucknow',
    role: 'Monsoon Bulletins & Quantitative Precipitation Forecasts',
    desc: 'Official weather advisories, yellow/orange/red alerts, and heavy precipitation warnings for Uttar Pradesh districts.',
    url: 'https://mausam.imd.gov.in/lucknow',
    type: 'Official Advisory Reference Link',
  },
  {
    title: 'UP Relief Commissioner (Rahat UP)',
    role: 'Disaster Relief Monitoring & Ex-Gratia Tracking',
    desc: 'Real-time state monitoring of relief camps, flood damage assessments, and emergency shelter coordination.',
    url: 'https://rahat.up.nic.in',
    type: 'Official Advisory Reference Link',
  },
];

export const PreparednessView: React.FC = () => {
  const { checklistState, toggleChecklistItem } = useApp();
  const [activeTab, setActiveTab] = useState<'flood' | 'drought' | 'contacts' | 'resources'>('flood');
  const [copiedPhone, setCopiedPhone] = useState<string | null>(null);
  const [searchContact, setSearchContact] = useState('');

  const handleCopyPhone = (phone: string) => {
    navigator.clipboard.writeText(phone);
    setCopiedPhone(phone);
    setTimeout(() => setCopiedPhone(null), 2000);
  };

  const filteredContacts = CONTACTS_DATA.filter(
    (c) =>
      c.title.toLowerCase().includes(searchContact.toLowerCase()) ||
      c.category.toLowerCase().includes(searchContact.toLowerCase()) ||
      c.role.toLowerCase().includes(searchContact.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Official Alert Distinction Banner */}
      <div className="p-3.5 rounded-2xl bg-navy-900/90 border border-cyan-800/60 text-xs text-slate-300 flex flex-col md:flex-row md:items-start justify-between gap-3">
        <div className="flex items-start space-x-3">
          <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="text-white">Decision-Support Notice:</strong> JalRakshak provides verified official
            reference links and community guidelines. It does <strong>not</strong> ingest live emergency alerts or
            issue official warnings. In case of an emergency, always follow evacuation instructions and alerts issued
            by the District Magistrate, UPSDMA, and Central Water Commission.
          </div>
        </div>
        <span className="text-[11px] px-2.5 py-1 rounded-lg bg-navy-800 text-cyan-300 border border-cyan-700/50 font-mono shrink-0">
          PROTOTYPE ADVISORY
        </span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-navy-800">
        <div>
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-950/70 px-2 py-0.5 rounded border border-emerald-800/80">
              Community Resilience
            </span>
            <span className="text-xs text-slate-400 font-mono">Action Guides & Contacts</span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-extrabold text-white mt-1">
            Preparedness & Safety
          </h1>
          <p className="text-xs lg:text-sm text-slate-300">
            Actionable emergency guidelines, persistent preparedness checklists and verified official government contacts.
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-navy-800 text-sm">
        {[
          { key: 'flood', label: 'Flood Preparedness', icon: Waves },
          { key: 'drought', label: 'Drought Preparedness', icon: Flame },
          { key: 'contacts', label: 'Emergency Contacts', icon: PhoneCall },
          { key: 'resources', label: 'Official Resources', icon: ExternalLink },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center space-x-2 px-4 py-2.5 font-medium border-b-2 transition-all ${
                activeTab === tab.key
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/30'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Panels */}
      {activeTab === 'flood' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-4">
            <Card variant="flood">
              <div className="flex items-center justify-between pb-3 border-b border-navy-800">
                <h3 className="text-base font-bold text-white flex items-center space-x-2">
                  <Waves className="w-5 h-5 text-cyan-400" />
                  <span>General Flood Action Guidelines (Gorakhpur / Eastern UP)</span>
                </h3>
                <span className="text-[11px] text-cyan-300 font-mono">
                  {Object.values(checklistState).filter(Boolean).length} / 5 Checked
                </span>
              </div>
              <div className="mt-4 space-y-3">
                {[
                  {
                    id: 'f1',
                    title: 'Follow official local warnings and evacuation orders promptly',
                    desc: 'Monitor official DM announcements and evacuate immediately when instructed by local authorities. Never delay evacuation.',
                  },
                  {
                    id: 'f2',
                    title: 'Keep emergency grab-bag ready with essential supplies',
                    desc: 'Drinking water, non-perishable food, flashlight, power bank, first-aid kit, and essential prescription medicines.',
                  },
                  {
                    id: 'f3',
                    title: 'Protect vital identification documents in waterproof packaging',
                    desc: 'Store Aadhaar cards, land records, voter IDs, and ration cards in sealed, waterproof plastic containers or pouches.',
                  },
                  {
                    id: 'f4',
                    title: 'Avoid floodwaters: Never walk, wade, or drive through moving water',
                    desc: 'Just 15 cm of moving water can sweep an adult off their feet; 30 cm can float vehicles. Avoid inundated roads and culverts.',
                  },
                  {
                    id: 'f5',
                    title: 'Know how to reach emergency relief services and high-ground shelters',
                    desc: 'Pre-identify designated municipal flood shelters, pucca schools, and district emergency helpline numbers (1070 / 1077).',
                  },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => toggleChecklistItem(item.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition flex items-start space-x-3.5 interactive-btn ${
                      checklistState[item.id]
                        ? 'bg-cyan-500/10 border-cyan-500/40'
                        : 'bg-navy-900/60 border-navy-800 hover:bg-navy-850'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 transition ${
                        checklistState[item.id]
                          ? 'bg-cyan-500 text-navy-950 font-bold'
                          : 'border border-slate-500 bg-navy-800'
                      }`}
                    >
                      {checklistState[item.id] && <CheckCircle2 className="w-4 h-4 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-white">{item.title}</div>
                      <div className="text-xs text-slate-300 mt-0.5 leading-relaxed">{item.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="lg:col-span-4 space-y-4">
            <Card className="bg-rose-950/40 border border-rose-800/40">
              <h4 className="text-sm font-bold text-rose-300 flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-rose-400" />
                <span>Life-Threatening Emergency?</span>
              </h4>
              <p className="mt-2 text-xs text-slate-200 leading-relaxed">
                If trapped by sudden riverine swelling, embankment breaches, or flash floods, immediately call state emergency authorities:
              </p>
              <div className="mt-3 p-3 rounded-xl bg-navy-950/80 border border-rose-900/50 space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">UP Disaster State Control</span>
                  <a href="tel:1070" className="font-mono font-bold text-cyan-300 text-sm hover:underline">1070</a>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">Gorakhpur DM Control Room</span>
                  <a href="tel:1077" className="font-mono font-bold text-cyan-300 text-sm hover:underline">1077</a>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400">National Emergency Number</span>
                  <a href="tel:112" className="font-mono font-bold text-cyan-300 text-sm hover:underline">112</a>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'drought' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-4">
            <Card variant="drought">
              <h3 className="text-base font-bold text-white pb-3 border-b border-navy-800 flex items-center space-x-2">
                <Flame className="w-5 h-5 text-amber-400" />
                <span>Drought Preparedness & Mitigation (Mahoba / Bundelkhand)</span>
              </h3>
              <div className="mt-4 space-y-3">
                {[
                  {
                    id: 'd1',
                    title: 'Monitor official water-supply and drought advisories',
                    desc: 'Regularly consult UP Jal Sansthan, Central Ground Water Board (CGWB), and district administration water notices.',
                  },
                  {
                    id: 'd2',
                    title: 'Practice safe water conservation and rainwater storage',
                    desc: 'Harvest rainwater in rooftop barrels and farm ponds (Khet Talab); repair leaks and recycle greywater safely.',
                  },
                  {
                    id: 'd3',
                    title: 'Follow locally issued agricultural and water-management guidance',
                    desc: 'Adopt micro-irrigation (drip/sprinkler) and plant drought-tolerant, certified short-duration pulse and oilseed varieties.',
                  },
                  {
                    id: 'd4',
                    title: 'Avoid unsupported claims about groundwater or crop health',
                    desc: 'Rely on verified local telemetry and Krishi Vigyan Kendra (KVK) bulletins rather than unverified commercial claims.',
                  },
                ].map((item) => (
                  <div
                    key={item.id}
                    onClick={() => toggleChecklistItem(item.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition flex items-start space-x-3.5 interactive-btn ${
                      checklistState[item.id]
                        ? 'bg-amber-500/10 border-amber-500/40'
                        : 'bg-navy-900/60 border-navy-800 hover:bg-navy-850'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 transition ${
                        checklistState[item.id]
                          ? 'bg-amber-500 text-navy-950 font-bold'
                          : 'border border-slate-500 bg-navy-800'
                      }`}
                    >
                      {checklistState[item.id] && <CheckCircle2 className="w-4 h-4 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-white">{item.title}</div>
                      <div className="text-xs text-slate-300 mt-0.5 leading-relaxed">{item.desc}</div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="lg:col-span-4 space-y-4">
            <Card variant="drought">
              <h4 className="text-sm font-bold text-amber-300 flex items-center space-x-2">
                <Heart className="w-4 h-4 text-amber-400" />
                <span>Bundelkhand Assistance Schemes</span>
              </h4>
              <p className="mt-2 text-xs text-slate-200 leading-relaxed">
                Farmers in Mahoba district can leverage PMKSY (Khet Talab farm pond scheme) and UP Agriculture drought relief funds.
              </p>
              <div className="mt-3 p-3 rounded-xl bg-navy-950/80 border border-amber-900/40 text-xs text-slate-300 space-y-1">
                <div>Mahoba Water Helpline: <strong className="text-amber-300">1077</strong></div>
                <div>Kisan Call Centre: <strong className="text-amber-300">1800-180-1551</strong></div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'contacts' && (
        <div className="space-y-4">
          {/* Search bar for contacts */}
          <div className="p-3 rounded-2xl bg-navy-900 border border-navy-800 flex items-center space-x-2.5 max-w-md">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={searchContact}
              onChange={(e) => setSearchContact(e.target.value)}
              placeholder="Filter by name, district, or role..."
              className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-full"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredContacts.map((c, i) => (
              <Card key={i} className="p-4 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                      {c.category}
                    </span>
                    <button
                      onClick={() => handleCopyPhone(c.fullPhone)}
                      className="text-slate-400 hover:text-cyan-300 flex items-center gap-1 text-[11px]"
                      title="Copy Phone"
                    >
                      {copiedPhone === c.fullPhone ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span className="text-emerald-400">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy</span>
                        </>
                      )}
                    </button>
                  </div>
                  <h4 className="font-bold text-sm text-white mt-2">{c.title}</h4>
                  <p className="text-xs text-slate-400 mt-1 leading-snug">{c.role}</p>
                </div>
                <div className="mt-4 pt-3 border-t border-navy-800 flex items-center justify-between">
                  <a
                    href={`tel:${c.phone}`}
                    className="font-mono text-cyan-300 hover:underline font-bold text-sm flex items-center gap-1"
                  >
                    <PhoneCall className="w-3 h-3" />
                    <span>{c.phone}</span>
                  </a>
                  <span className="text-[11px] text-slate-400 font-mono">{c.website}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'resources' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {OFFICIAL_RESOURCES.map((res, i) => (
            <Card key={i} className="p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/80 font-mono">
                    {res.type}
                  </span>
                  <a
                    href={res.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-cyan-400 hover:text-cyan-300 transition"
                    title={`Open ${res.title}`}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
                <h4 className="font-bold text-sm text-white">{res.title}</h4>
                <div className="text-xs text-cyan-300 font-medium mt-0.5">{res.role}</div>
                <p className="text-xs text-slate-300 mt-2 leading-relaxed">{res.desc}</p>
              </div>
              <div className="mt-4 pt-2 border-t border-navy-800 flex items-center justify-between text-[11px] text-cyan-300 font-mono">
                <a
                  href={res.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="hover:underline flex items-center gap-1"
                >
                  <span>{res.url}</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
                <span className="text-slate-500 text-[10px]">Reference Link</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
