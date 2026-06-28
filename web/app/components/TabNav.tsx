'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const TABS = [
  { href: '/', label: '⚽ 球队' },
  { href: '/schedule', label: '📅 赛程' },
  { href: '/config', label: '🎛️ 配置' },
  { href: '/predict', label: '🏆 预测' },
];

export function TabNav() {
  const pathname = usePathname();
  return (
    <nav className="tab-nav">
      {TABS.map((t) => (
        <Link
          key={t.href}
          href={t.href}
          className={`tab-link ${pathname === t.href ? 'active' : ''}`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
