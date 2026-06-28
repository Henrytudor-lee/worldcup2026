'use client';

import { useState } from 'react';
import type { Weights, Preset } from '../lib/types';

interface Props {
  initialWeights: Weights;
  presets: Record<string, Preset>;
}

const GROUPS: Array<{
  key: keyof Weights;
  label: string;
  description: string;
}> = [
  { key: 'position_top_n', label: '位置 Top N', description: '锋线/中场/后卫/门将 取 Top N 球员' },
  { key: 'status_weights', label: '状态权重', description: '身价/进球/助攻 权重' },
  { key: 'nat_intl', label: '国家队 G/A', description: '国家队进球/助攻 权重' },
  { key: 'def_gk_weights', label: '防守/门将权重', description: '后卫/门将权重' },
  { key: 'player_to_total', label: '球员→总评', description: '球员 → 总评分 比例' },
  { key: 'smoothing', label: '平滑/异常', description: '平滑因子 / 异常值处理' },
];

export function ConfigClient({ initialWeights, presets }: Props) {
  const [weights, setWeights] = useState<Weights>(initialWeights);
  const [activePreset, setActivePreset] = useState<string>('default');

  const update = (group: keyof Weights, key: string, value: number) => {
    setWeights((prev) => ({
      ...prev,
      [group]: { ...(prev[group] as any), [key]: value },
    }));
    setActivePreset('custom');
  };

  const applyPreset = (presetName: string) => {
    if (presetName === 'default') {
      setWeights(initialWeights);
      setActivePreset('default');
    } else if (presets[presetName]) {
      setWeights(presets[presetName].weights);
      setActivePreset(presetName);
    }
  };

  return (
    <div>
      <h2 className="section-title">
        🎛️ 算法系数配置
        <span className="count-badge">23 系数 + 6 预设</span>
      </h2>

      <div className="config-section">
        <h3>预设 (PRESETS)</h3>
        <div className="preset-buttons">
          <button
            className={`preset-btn ${activePreset === 'default' ? 'active' : ''}`}
            onClick={() => applyPreset('default')}
          >
            默认（均衡）
          </button>
          {Object.entries(presets).map(([key, p]) => (
            <button
              key={key}
              className={`preset-btn ${activePreset === key ? 'active' : ''}`}
              onClick={() => applyPreset(key)}
            >
              {p.name || key}
            </button>
          ))}
        </div>
        <p className="muted">
          选中预设后所有滑块会自动跳到该预设的系数值。当前生效:
          <strong style={{ color: 'var(--accent)', marginLeft: 4 }}>
            {activePreset}
          </strong>
        </p>
      </div>

      {GROUPS.map(({ key, label, description }) => {
        const group = weights[key] as Record<string, number> | undefined;
        if (!group) return null;
        return (
          <div key={String(key)} className="config-section">
            <h3>
              {label}
              <span className="muted" style={{ marginLeft: 8, fontSize: 12, fontWeight: 'normal' }}>
                {description}
              </span>
            </h3>
            {Object.entries(group).map(([k, v]) => (
              <div key={k} className="weight-row">
                <span className="label">{k}</span>
                <input
                  type="range"
                  min={0}
                  max={50}
                  step={0.5}
                  value={v}
                  onChange={(e) => update(key, k, parseFloat(e.target.value))}
                />
                <span className="val">{v.toFixed(2)}</span>
              </div>
            ))}
          </div>
        );
      })}

      <div className="config-section">
        <p className="muted">
          ⚠️ 当前滑块仅做本地显示，权重变更实际重算 104 场需要后端服务
          <code style={{ marginLeft: 4 }}>backend/server.py</code> 在
          <code style={{ marginLeft: 4 }}>localhost:8766</code> 运行。
          启动命令: <code>cd backend &amp;&amp; python3 server.py</code>
        </p>
      </div>
    </div>
  );
}
