'use client';

import Image from 'next/image';

export interface CoachIntroProps {
  /** Opening name to greet the player with. */
  openingName?: string;
  headline: string;
  message: string;
}

/** Highlights-mode coach greeting (avatar + speech bubble, Part B). */
export default function CoachIntro({ openingName, headline, message }: CoachIntroProps) {
  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }} data-testid="coach-intro">
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: '50%',
          flex: 'none',
          padding: 3,
          background: 'var(--review-cta-gradient)',
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#fff',
          }}
        >
          <Image
            src="/static/images/chesster-logo-v3.png"
            alt=""
            width={44}
            height={44}
          />
        </div>
      </div>
      <div
        className="review-card"
        style={{
          flex: 1,
          padding: '12px 14px',
          position: 'relative',
          borderRadius: 12,
        }}
      >
        <div
          className="review-heading"
          style={{ fontWeight: 800, fontSize: 15, marginBottom: 6 }}
        >
          {headline}
        </div>
        <p style={{ fontSize: 13, lineHeight: 1.45, opacity: 0.85, margin: 0 }}>{message}</p>
        {openingName && (
          <div
            style={{
              fontSize: 11.5,
              marginTop: 8,
              opacity: 0.6,
              textDecoration: 'underline',
            }}
          >
            {openingName}
          </div>
        )}
      </div>
    </div>
  );
}
