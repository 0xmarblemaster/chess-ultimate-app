'use client';

import { useRef, useState } from 'react';

type AssetKind = 'item_art' | 'legion_crest' | 'rank_icon';

interface AssetUploadProps {
  orgId: string;
  kind: AssetKind;
  value: string;
  onChange: (url: string) => void;
  placeholder?: string;
  /** Preview + Upload button only, no URL field (tight grid cells like ranks). */
  compact?: boolean;
  className?: string;
}

const ACCEPT = 'image/png,image/jpeg,image/webp,image/svg+xml';

/**
 * Art/crest/icon uploader — reuses the branding/upload contract (§9.4, D-9):
 * POST multipart to the gamification upload proxy, which returns `{ url }`; the
 * URL is handed back via onChange to store on the catalog row. Assets are
 * swappable without schema impact. Full mode keeps a URL field so a path can
 * still be pasted; compact mode shows only a preview + Upload button.
 */
export function AssetUpload({
  orgId,
  kind,
  value,
  onChange,
  placeholder,
  compact = false,
  className,
}: AssetUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      form.append('kind', kind);
      const res = await fetch(`/api/admin/organizations/${orgId}/gamification/upload`, {
        method: 'POST',
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.url) {
        setError(data.error || 'Upload failed');
        return;
      }
      onChange(data.url as string);
    } catch {
      setError('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const hiddenInput = (
    <input
      ref={fileRef}
      type="file"
      accept={ACCEPT}
      className="hidden"
      onChange={(e) => {
        const f = e.target.files?.[0];
        if (f) upload(f);
        e.target.value = '';
      }}
    />
  );

  if (compact) {
    return (
      <div className={className}>
        <div className="flex flex-col items-center gap-1">
          {value ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={value} alt="" className="w-10 h-10 rounded border border-gray-100 object-contain" />
          ) : (
            <div className="w-10 h-10 rounded border border-dashed border-gray-300 flex items-center justify-center text-gray-300 text-lg">
              ＋
            </div>
          )}
          {hiddenInput}
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="text-xs text-purple-600 disabled:opacity-50"
          >
            {uploading ? '…' : 'Upload'}
          </button>
        </div>
        {error && <p className="text-xs text-red-500 mt-1 text-center">{error}</p>}
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="flex gap-2">
        <input
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 rounded-lg border border-gray-300 px-2 py-1 text-sm"
        />
        {hiddenInput}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="rounded-lg bg-gray-100 text-gray-700 px-3 py-1 text-sm font-medium disabled:opacity-50 whitespace-nowrap"
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
      </div>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}
