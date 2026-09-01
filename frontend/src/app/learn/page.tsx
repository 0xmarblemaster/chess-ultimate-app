import { resolveCeLevelFloor } from '@/lib/learn-ce-floor';
import LearnClient from './LearnClient';

export const dynamic = 'force-dynamic';

export default async function LearnPage() {
  const ceLevelFloor = await resolveCeLevelFloor();
  return <LearnClient ceLevelFloor={ceLevelFloor} />;
}
