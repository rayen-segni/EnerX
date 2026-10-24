import type { Holdings, KycRecord, Listing, ProductionEvent, Profile, Project } from './types'
import { OWNER_RETAINED, TOTAL_SUPPLY, splitRevenue } from './utils'

export const INITIAL_PROFILES: Profile[] = [
  { id: 'user-1', backendId: 1, name: 'Rayen Segni', email: 'contact.rayen@gmail.com', role: 'User', balance: 12000, initials: 'RS', hederaAccount: '0.0.10652075' },
  { id: 'user-2', backendId: 2, name: 'Amen Beji', email: 'contact.beji@gmail.com', role: 'User', balance: 25000, initials: 'AB', hederaAccount: '0.0.10794965' },
  { id: 'user-3', backendId: 3, name: 'Yassine Ammamo', email: 'contact.yassin@gmail.com', role: 'User', balance: 18000, initials: 'YA', hederaAccount: '0.0.10872211' },
]

export const INITIAL_KYC: Record<string, KycRecord> = {
  'user-1': {
    verified: false,
    did: null,
    identityVerified: false,
    investorVerified: false,
    ownerVerified: false,
    legalName: 'Rayen Segni',
  },
  'user-2': {
    verified: false,
    did: null,
    identityVerified: false,
    investorVerified: false,
    ownerVerified: false,
  },
  'user-3': {
    verified: false,
    did: null,
    identityVerified: false,
    investorVerified: false,
    ownerVerified: false,
    legalName: 'Yassine Ammamo',
  },
}

const baseProject = { ownerId: 'user-1', totalSupply: TOTAL_SUPPLY, ownerRetained: OWNER_RETAINED }

export const INITIAL_PROJECTS: Project[] = [
  {
    ...baseProject,
    id: 'p-sbs',
    name: 'Sidi Bou Saïd Rooftop Array',
    location: 'Sidi Bou Saïd, Tunis',
    region: 'Tunis',
    description: '48 kWp distributed across 22 whitewashed rooftops, injecting into the STEG grid during evening peak.',
    targetFunding: 84000,
    tokenName: 'Sidi Bou Said Solar',
    tokenSymbol: 'SBS',
    hederaTokenId: '0.0.4821937',
    availableTokens: 0,
    capacityKwp: 48,
  },
  {
    ...baseProject,
    id: 'p-hsm',
    name: 'Houmt Souk Microgrid',
    location: 'Houmt Souk, Djerba',
    region: 'Djerba',
    description: 'Island microgrid with battery buffering to offset summer tourism demand spikes.',
    targetFunding: 49000,
    tokenName: 'Houmt Souk Energy',
    tokenSymbol: 'HSM',
    hederaTokenId: '0.0.4822104',
    availableTokens: 46,
    capacityKwp: 32,
  },
  {
    ...baseProject,
    id: 'p-tzo',
    name: 'Tozeur Oasis Canopy',
    location: 'Tozeur Oasis',
    region: 'Tozeur',
    description: 'High-irradiance desert canopy shading palm groves while feeding the southern STEG feeder.',
    targetFunding: 126000,
    tokenName: 'Tozeur Oasis Power',
    tokenSymbol: 'TZO',
    hederaTokenId: '0.0.4823550',
    availableTokens: 70,
    capacityKwp: 72,
  },
  {
    ...baseProject,
    id: 'p-sfx',
    name: 'Sfax Medina Rooftops',
    location: 'Medina, Sfax',
    region: 'Sfax',
    description: 'Retrofit of historic medina rooftops with low-profile bifacial modules.',
    targetFunding: 56000,
    tokenName: 'Sfax Medina Solar',
    tokenSymbol: 'SFX',
    hederaTokenId: '0.0.4824012',
    availableTokens: 58,
    capacityKwp: 36,
  },
]

export const INITIAL_HOLDINGS: Holdings = {
  'p-sbs': { 'user-1': 30, 'user-2': 40, 'user-3': 30 },
  'p-hsm': { 'user-1': 30, 'user-3': 24 },
  'p-tzo': { 'user-1': 30 },
  'p-sfx': { 'user-1': 30, 'user-2': 12 },
}

export const INITIAL_LISTINGS: Listing[] = [
  { id: 'l-1', projectId: 'p-sbs', sellerId: 'user-3', amount: 5, unitPrice: 1290 },
  { id: 'l-2', projectId: 'p-sfx', sellerId: 'user-2', amount: 4, unitPrice: 860 },
]

const seedEvent = (id: string, timestamp: string, txId: string): ProductionEvent => ({
  id,
  projectId: 'p-sbs',
  timestamp,
  energy_kwh: '520.00',
  revenue: '104.00',
  contract_transaction_id: txId,
  distribution: splitRevenue('104.00', INITIAL_PROJECTS[0], INITIAL_HOLDINGS['p-sbs'], INITIAL_PROFILES),
})

export const INITIAL_HISTORY: ProductionEvent[] = [
  seedEvent('e-2', '2026-10-10T18:00:00Z', '0.0.5123408@1791655200.418220931'),
  seedEvent('e-1', '2026-10-09T18:00:00Z', '0.0.5123408@1791568800.902117345'),
]
