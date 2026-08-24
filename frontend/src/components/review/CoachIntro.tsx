'use client';

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
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 34,
          background: 'var(--review-cta-gradient)',
        }}
      >
        🐼
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
