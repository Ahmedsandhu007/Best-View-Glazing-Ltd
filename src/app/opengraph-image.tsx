import { ImageResponse } from "next/og";
import { site } from "@/content/site";

export const alt = `${site.name} – Window & Door Repairs London`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#202C30",
          color: "#FFFFFF",
          padding: 72,
          fontFamily: "Arial, Helvetica, sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <svg width="72" height="72" viewBox="0 0 40 40">
            <rect x="2.25" y="2.25" width="35.5" height="35.5" fill="none" stroke="#FFFFFF" strokeWidth="2.5" />
            <path d="M20 2.25v35.5M2.25 20h35.5" fill="none" stroke="#FFFFFF" strokeWidth="2" />
            <rect x="23.5" y="23.5" width="11" height="11" fill="#C5A477" />
          </svg>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: 40, fontWeight: 700, letterSpacing: -1 }}>Best View</div>
            <div style={{ fontSize: 18, letterSpacing: 4, textTransform: "uppercase", color: "rgba(255,255,255,0.7)" }}>Glazing Ltd</div>
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ width: 72, height: 4, background: "#C5A477" }} />
          <div style={{ fontSize: 60, fontWeight: 700, lineHeight: 1.1, letterSpacing: -1.5, maxWidth: 900 }}>
            Professional Window &amp; Door Repairs Across London
          </div>
          <div style={{ fontSize: 26, color: "rgba(255,255,255,0.75)" }}>
            uPVC · Aluminium · Timber · Sash · Double Glazing · Locks &amp; Hinges
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
