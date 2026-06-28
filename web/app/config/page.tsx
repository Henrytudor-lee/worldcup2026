import { fetchWeights } from '../lib/data';
import { ConfigClient } from './ConfigClient';

export const dynamic = 'force-dynamic';

export default async function ConfigPage() {
  let weights;
  try {
    weights = await fetchWeights();
  } catch (e) {
    console.error('Failed to load weights:', e);
    weights = { default: {} as any, presets: {} as any };
  }
  return <ConfigClient initialWeights={weights.default} presets={weights.presets} />;
}
