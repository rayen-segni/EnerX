'use client'

import Image from 'next/image'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { BrainCircuit, Building2, Home, Menu, Store, TrendingUp, X } from 'lucide-react'
import type { KycRecord, Profile, TabId } from '@/lib/enerx/types'
import { cn } from '@/lib/utils'
import { ProfileMenu } from './profile-menu'
import enerxLogo from '../../enerx.png'

const TABS: { id: TabId; label: string; icon: typeof Home }[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'invest', label: 'Invest', icon: TrendingUp },
  { id: 'marketplace', label: 'Marketplace', icon: Store },
  { id: 'owner', label: 'Operate', icon: Building2 },
  { id: 'ai', label: 'AI Predictor', icon: BrainCircuit },
]

interface TopNavProps {
  activeTab: TabId
  onTabChange: (tab: TabId) => void
  profiles: Profile[]
  activeProfile: Profile
  kycRecords: Record<string, KycRecord>
  onProfileChange: (id: string) => void
}

export function TopNav({ activeTab, onTabChange, profiles, activeProfile, kycRecords, onProfileChange }: TopNavProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [portalReady, setPortalReady] = useState(false)

  useEffect(() => {
    setPortalReady(true)
  }, [])

  useEffect(() => {
    if (!mobileNavOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setMobileNavOpen(false)
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [mobileNavOpen])

  const tabButtons = (layout: 'desktop' | 'mobile') =>
    TABS.map(({ id, label, icon: Icon }) => {
      const active = activeTab === id
      return (
        <button
          key={id}
          type="button"
          onClick={() => {
            onTabChange(id)
            if (layout === 'mobile') setMobileNavOpen(false)
          }}
          aria-current={active ? 'page' : undefined}
          className={cn(
            'relative flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition',
            layout === 'mobile'
              ? active
                ? 'bg-slate-800 text-white shadow-[inset_0_0_0_1px_rgba(255,102,34,0.4)]'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              : active
                ? 'bg-white/[0.06] text-white shadow-[inset_0_0_0_1px_rgba(255,102,34,0.4)]'
                : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-100',
            layout === 'mobile' && 'w-full justify-start px-3 py-3 text-base',
          )}
        >
          <Icon className={cn('size-4', active ? 'text-solar' : 'text-slate-500')} aria-hidden />
          {label}
          {active && (
            <span
              className={cn(
                'absolute bg-solar shadow-[0_0_10px_2px_rgba(255,102,34,0.6)]',
                layout === 'mobile'
                  ? 'inset-y-2 left-0 w-px'
                  : 'inset-x-3 -bottom-[9px] h-px',
              )}
              aria-hidden
            />
          )}
        </button>
      )
    })

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#020617] md:bg-slate-950/80 md:backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 md:px-6">
        <button
          type="button"
          onClick={() => setMobileNavOpen(true)}
          aria-label="Open navigation menu"
          aria-expanded={mobileNavOpen}
          aria-controls="mobile-navigation"
          className="flex size-10 shrink-0 items-center justify-center rounded-lg text-slate-300 transition hover:bg-white/[0.06] hover:text-white md:hidden"
        >
          <Menu className="size-5" aria-hidden />
        </button>
        <button
          type="button"
          onClick={() => onTabChange('home')}
          className="flex items-center gap-2.5"
          aria-label="EnerX home"
        >
          <Image src={enerxLogo} alt="EnerX logo" width={30} height={38} priority className="h-9 w-auto object-contain" />
          <span className="text-xl font-bold tracking-tight text-white">
            Ener<span className="text-solar">X</span>
          </span>
        </button>

        <nav aria-label="Primary" className="ml-4 hidden items-center gap-1 md:flex">
          {tabButtons('desktop')}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <span className="hidden items-center gap-2 rounded-full border border-ledger/40 bg-ledger/10 px-3 py-1 font-mono text-[11px] font-semibold tracking-wider text-ledger sm:flex">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-ledger opacity-75" />
              <span className="relative inline-flex size-2 rounded-full bg-ledger" />
            </span>
            HEDERA TESTNET
          </span>
          <ProfileMenu
            profiles={profiles}
            activeProfile={activeProfile}
            kycRecords={kycRecords}
            onChange={onProfileChange}
          />
        </div>
      </div>
      {portalReady &&
        createPortal(
          <div
            className={cn(
              'fixed inset-0 z-[100] md:hidden',
              mobileNavOpen ? 'opacity-100' : 'pointer-events-none opacity-0',
            )}
            aria-hidden={!mobileNavOpen}
          >
            <button
              type="button"
              aria-label="Close navigation menu"
              onClick={() => setMobileNavOpen(false)}
              tabIndex={mobileNavOpen ? 0 : -1}
              className="absolute inset-0 bg-slate-950/55 backdrop-blur-sm"
            />
            <nav
              id="mobile-navigation"
              aria-label="Primary mobile"
              inert={!mobileNavOpen}
              className={cn(
                'absolute inset-y-0 left-0 flex w-[min(18rem,85vw)] flex-col border-r border-slate-700 bg-[#020617] px-4 py-5 shadow-2xl transition-transform duration-200 ease-out',
                mobileNavOpen ? 'translate-x-0' : '-translate-x-full',
              )}
            >
              <div className="mb-8 flex items-center justify-between">
                <span className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Navigation</span>
                <button
                  type="button"
                  onClick={() => setMobileNavOpen(false)}
                  aria-label="Close navigation menu"
                  className="flex size-10 items-center justify-center rounded-lg text-slate-300 transition hover:bg-slate-800 hover:text-white"
                >
                  <X className="size-5" aria-hidden />
                </button>
              </div>
              <div className="flex flex-col gap-1">{tabButtons('mobile')}</div>
            </nav>
          </div>,
          document.body,
        )}
    </header>
  )
}
