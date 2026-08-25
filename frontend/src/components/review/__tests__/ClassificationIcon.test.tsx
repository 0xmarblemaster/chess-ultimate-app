/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import ClassificationIcon, {
  CLASSIFICATION_COLORS,
  type Classification,
} from '../ClassificationIcon';
import { renderIntl, gameReview } from './intl';

afterEach(cleanup);

const ALL: Classification[] = [
  'brilliant',
  'great',
  'best',
  'excellent',
  'good',
  'book',
  'inaccuracy',
  'mistake',
  'miss',
  'blunder',
  'forced',
];

describe('ClassificationIcon', () => {
  it('renders every classification with the exact palette fill on the disc', () => {
    for (const type of ALL) {
      const { container, unmount } = renderIntl(<ClassificationIcon type={type} size={24} />);
      const svg = container.querySelector('svg')!;
      expect(svg).toBeTruthy();
      expect(svg.getAttribute('viewBox')).toBe('0 0 18 19');
      expect(svg.getAttribute('data-classification')).toBe(type);
      // The colored disc path carries the frozen palette hex.
      const color = CLASSIFICATION_COLORS[type];
      const discPath = Array.from(svg.querySelectorAll('path')).find(
        (p) => p.getAttribute('fill')?.toLowerCase() === color.toLowerCase(),
      );
      expect(discPath, `disc fill for ${type}`).toBeTruthy();
      unmount();
    }
  });

  it('exposes an accessible label per type', () => {
    const { container } = renderIntl(<ClassificationIcon type="brilliant" />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('aria-label')).toBe(gameReview.classifications.brilliant);
  });

  it('sizes to a fixed pixel value when size is given', () => {
    const { container } = renderIntl(<ClassificationIcon type="best" size={18} />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('width')).toBe('18px');
    expect(svg.getAttribute('height')).toBe('18px');
  });

  it('fills its parent (100%) when no size is given', () => {
    const { container } = renderIntl(<ClassificationIcon type="book" />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('width')).toBe('100%');
  });
});
