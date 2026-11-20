import * as React from "react";

/**
 * "Where does this show up?" panels for the CMS: a small picture of the page
 * with the part being edited highlighted, plus numbered directions.
 * A collection or field opts in through `guide` in the CMS registry.
 */
export type FieldGuide = { diagram: string; title: string; steps: string[] };

const BG = "#f5f3ed";
const BLOCK = "#d9ded9";
const DARK = "#202c30";
const HOT = "#176b65";
const BRASS = "#c5a477";

function Marker({ x, y, n }: { x: number; y: number; n: number }) {
  return (
    <g>
      <circle cx={x} cy={y} r="9" fill={HOT} />
      <text x={x} y={y + 3.5} textAnchor="middle" fontSize="10" fontWeight="700" fill="#fff">
        {n}
      </text>
    </g>
  );
}

const Line = ({ x, y, w, h = 5, hot = false }: { x: number; y: number; w: number; h?: number; hot?: boolean }) => (
  <rect x={x} y={y} width={w} height={h} rx={h / 2} fill={hot ? HOT : BLOCK} />
);

const Box = ({ x, y, w, h, hot = false, fill = "#fff" }: { x: number; y: number; w: number; h: number; hot?: boolean; fill?: string }) => (
  <rect x={x} y={y} width={w} height={h} rx="3" fill={fill} stroke={hot ? HOT : BLOCK} strokeWidth={hot ? 2 : 1} />
);

/** Thin top bar so every picture reads as "a page of the website". */
const Chrome = () => (
  <>
    <rect x="0" y="0" width="320" height="180" rx="6" fill={BG} />
    <rect x="0" y="0" width="320" height="16" rx="6" fill="#fff" />
    <rect x="10" y="4" width="8" height="8" fill="none" stroke={DARK} strokeWidth="1.5" />
    <rect x="22" y="6" width="30" height="4" rx="2" fill={DARK} />
    <rect x="130" y="6" width="60" height="4" rx="2" fill={BLOCK} />
    <rect x="266" y="4" width="44" height="8" rx="2" fill={HOT} />
  </>
);

const DIAGRAMS: Record<string, React.ReactNode> = {
  // Home page hero
  homeHero: (
    <>
      <Chrome />
      <Line x={24} y={34} w={60} h={4} hot />
      <Line x={24} y={46} w={130} h={10} hot />
      <Line x={24} y={62} w={100} h={10} hot />
      <Line x={24} y={84} w={140} h={4} />
      <Line x={24} y={93} w={120} h={4} />
      <rect x={24} y={108} width={64} height={16} rx="2" fill={HOT} />
      <rect x={96} y={108} width={64} height={16} rx="2" fill="none" stroke={DARK} />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <path d={`M26 ${140 + i * 10} l3 3 l5 -6`} fill="none" stroke={HOT} strokeWidth="1.5" />
          <Line x={38} y={138 + i * 10} w={80 + i * 10} h={4} />
        </g>
      ))}
      <Box x={186} y={30} w={114} h={136} fill={BLOCK} />
      <Marker x={96} y={36} n={1} />
      <Marker x={170} y={60} n={2} />
      <Marker x={172} y={116} n={3} />
      <Marker x={150} y={150} n={4} />
      <Marker x={300} y={160} n={5} />
    </>
  ),
  // Centred heading above a block
  heading: (
    <>
      <Chrome />
      <Line x={24} y={36} w={52} h={4} hot />
      <Line x={24} y={50} w={180} h={10} hot />
      <Line x={24} y={70} w={220} h={4} hot />
      {[0, 1, 2].map((i) => (
        <Box key={i} x={24 + i * 94} y={94} w={84} h={66} />
      ))}
      <Marker x={90} y={38} n={1} />
      <Marker x={216} y={55} n={2} />
      <Marker x={258} y={72} n={3} />
      <Marker x={160} y={127} n={4} />
    </>
  ),
  // Dark banner at the top of a page
  hero: (
    <>
      <Chrome />
      <rect x="0" y="16" width="320" height="86" fill={DARK} />
      <Line x={24} y={32} w={50} h={4} hot={false} />
      <rect x={24} y={32} width={50} height={4} rx="2" fill={BRASS} />
      <Line x={24} y={46} w={190} h={10} hot />
      <Line x={24} y={62} w={130} h={10} hot />
      <Line x={24} y={82} w={170} h={4} />
      <Line x={24} y={91} w={140} h={4} />
      <Line x={24} y={116} w={120} h={6} />
      <Line x={24} y={130} w={240} h={4} />
      <Line x={24} y={139} w={220} h={4} />
      <Line x={24} y={148} w={200} h={4} />
      <Marker x={232} y={56} n={1} />
      <Marker x={210} y={88} n={2} />
      <Marker x={290} y={134} n={3} />
    </>
  ),
  // Photographs on the pages
  photos: (
    <>
      <Chrome />
      <Line x={24} y={34} w={100} h={8} />
      <Line x={24} y={50} w={120} h={4} />
      <Line x={24} y={59} w={100} h={4} />
      <Box x={170} y={28} w={130} h={70} hot fill={BLOCK} />
      <Box x={24} y={110} w={100} h={54} hot fill={BLOCK} />
      <Box x={136} y={110} w={48} h={36} hot fill={BLOCK} />
      <Box x={190} y={110} w={48} h={36} hot fill={BLOCK} />
      <Line x={250} y={116} w={50} h={6} />
      <Line x={250} y={128} w={46} h={4} />
      <Line x={250} y={137} w={40} h={4} />
      <Marker x={235} y={63} n={1} />
      <Marker x={74} y={137} n={2} />
      <Marker x={300} y={158} n={3} />
    </>
  ),
  // The enquiry form's dropdowns
  form: (
    <>
      <Chrome />
      <Box x={20} y={30} w={280} h={138} />
      <Line x={32} y={42} w={60} h={4} />
      <Box x={32} y={50} w={120} h={14} />
      <Line x={168} y={42} w={60} h={4} />
      <Box x={168} y={50} w={120} h={14} />
      <Line x={32} y={76} w={50} h={4} />
      <Box x={32} y={84} w={120} h={14} hot />
      <path d="M140 89 l4 4 l4 -4" fill="none" stroke={HOT} strokeWidth="1.5" />
      <Line x={168} y={76} w={60} h={4} />
      <Box x={168} y={84} w={120} h={14} hot />
      <path d="M276 89 l4 4 l4 -4" fill="none" stroke={HOT} strokeWidth="1.5" />
      <Line x={32} y={110} w={70} h={4} />
      <Box x={32} y={118} w={120} h={14} hot />
      <path d="M140 123 l4 4 l4 -4" fill="none" stroke={HOT} strokeWidth="1.5" />
      <rect x={32} y={144} width={70} height={14} rx="2" fill={HOT} />
      <Marker x={20} y={91} n={1} />
      <Marker x={300} y={91} n={2} />
      <Marker x={20} y={125} n={3} />
    </>
  ),
  // Google search result
  seo: (
    <>
      <rect x="0" y="0" width="320" height="180" rx="6" fill="#fff" stroke={BLOCK} />
      <rect x="20" y="18" width="200" height="18" rx="9" fill={BG} stroke={BLOCK} />
      <Line x={20} y={56} w={90} h={4} />
      <Line x={20} y={68} w={210} h={8} hot />
      <Line x={20} y={86} w={270} />
      <Line x={20} y={96} w={230} />
      <Line x={20} y={124} w={80} h={4} />
      <Line x={20} y={136} w={180} h={8} />
      <Line x={20} y={154} w={250} />
      <Marker x={246} y={72} n={1} />
      <Marker x={304} y={91} n={2} />
      <Marker x={300} y={140} n={3} />
    </>
  ),
  // Footer
  footer: (
    <>
      <rect x="0" y="0" width="320" height="180" rx="6" fill={BG} />
      <Line x={40} y={14} w={160} />
      <Line x={40} y={24} w={120} />
      <rect x="0" y="40" width="320" height="140" fill={DARK} />
      <rect x={20} y={54} width={10} height={10} fill="none" stroke="#fff" strokeWidth="1.5" />
      <Line x={36} y={56} w={50} h={5} />
      <Line x={20} y={74} w={100} h={4} hot />
      <Line x={20} y={83} w={90} h={4} hot />
      <Line x={20} y={92} w={70} h={4} hot />
      <rect x={20} y={106} width={60} height={5} rx="2" fill={BRASS} />
      {[0, 1, 2].map((c) => (
        <g key={c}>
          <rect x={150 + c * 54} y={56} width={36} height={5} rx="2" fill={BRASS} />
          {[0, 1, 2, 3].map((r) => (
            <Line key={r} x={150 + c * 54} y={70 + r * 11} w={30 + ((r + c) % 3) * 6} h={3} />
          ))}
        </g>
      ))}
      <line x1="0" x2="320" y1="150" y2="150" stroke="#35434a" />
      <Line x={20} y={160} w={90} h={4} />
      <Line x={200} y={160} w={100} h={4} hot />
      <Marker x={132} y={84} n={1} />
      <Marker x={300} y={58} n={2} />
      <Marker x={186} y={162} n={3} />
    </>
  ),
  // Legal page
  legal: (
    <>
      <Chrome />
      <rect x="0" y="16" width="320" height="34" fill={DARK} />
      <Line x={24} y={30} w={110} h={8} />
      <Line x={24} y={60} w={70} h={4} hot />
      <Line x={24} y={76} w={120} h={8} hot />
      <Line x={24} y={92} w={270} />
      <Line x={24} y={102} w={250} />
      {[0, 1].map((i) => (
        <g key={i}>
          <circle cx={30} cy={119 + i * 10} r="2" fill={HOT} />
          <Line x={38} y={117 + i * 10} w={200} h={4} />
        </g>
      ))}
      <Line x={24} y={146} w={100} h={8} />
      <Line x={24} y={162} w={260} />
      <Marker x={108} y={62} n={1} />
      <Marker x={158} y={80} n={2} />
      <Marker x={300} y={120} n={3} />
    </>
  ),
  // Service card
  tile: (
    <>
      <Chrome />
      <Box x={20} y={30} w={86} h={136} />
      <Box x={117} y={30} w={86} h={136} hot />
      <Box x={214} y={30} w={86} h={136} />
      <rect x={118} y={31} width={84} height={50} fill={BLOCK} />
      <Line x={126} y={92} w={60} h={6} hot />
      <Line x={126} y={106} w={70} />
      <Line x={126} y={116} w={60} />
      <Line x={126} y={126} w={66} />
      <Line x={126} y={148} w={40} h={5} hot />
      <Marker x={160} y={56} n={1} />
      <Marker x={112} y={95} n={2} />
      <Marker x={112} y={118} n={3} />
      <Marker x={190} y={150} n={4} />
    </>
  ),
  // Areas grid
  areas: (
    <>
      <Chrome />
      {[0, 1, 2, 3, 4].map((c) => (
        <g key={c}>
          <rect x={16 + c * 59} y={36} width={50} height={2} fill={DARK} />
          <Line x={16 + c * 59} y={44} w={44} h={6} hot={c === 1} />
          <Line x={16 + c * 59} y={56} w={48} h={3} hot={c === 1} />
          <Line x={16 + c * 59} y={62} w={40} h={3} hot={c === 1} />
          {[0, 1, 2, 3, 4].map((r) => (
            <Line key={r} x={16 + c * 59} y={76 + r * 12} w={28 + ((r + c) % 3) * 8} h={4} hot={c === 1 && r === 0} />
          ))}
        </g>
      ))}
      <Marker x={120} y={40} n={1} />
      <Marker x={132} y={64} n={2} />
      <Marker x={120} y={110} n={3} />
      <Box x={16} y={146} w={288} h={22} fill={BG} />
    </>
  ),
  // FAQ accordion
  faq: (
    <>
      <Chrome />
      <Line x={24} y={34} w={120} h={8} />
      <Box x={24} y={56} w={272} h={110} />
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <Line x={36} y={68 + i * 26} w={i === 0 ? 150 : 110 + i * 14} h={6} hot={i === 0} />
          <path d={`M278 ${68 + i * 26} l4 4 l4 -4`} fill="none" stroke={HOT} strokeWidth="1.5" />
          {i < 3 ? <line x1="24" x2="296" y1={82 + i * 26} y2={82 + i * 26} stroke={BLOCK} /> : null}
        </g>
      ))}
      <Marker x={160} y={38} n={1} />
      <Marker x={300} y={71} n={2} />
    </>
  ),
  // Testimonial card
  testimonial: (
    <>
      <Chrome />
      <Box x={60} y={30} w={200} h={136} hot />
      <text x="74" y="56" fontSize="22" fontWeight="700" fill={BRASS}>
        “
      </text>
      {[0, 1, 2, 3, 4].map((i) => (
        <circle key={i} cx={96 + i * 12} cy={48} r="4" fill={i < 4 ? BRASS : BLOCK} />
      ))}
      <Line x={74} y={68} w={170} />
      <Line x={74} y={79} w={160} />
      <Line x={74} y={90} w={130} />
      <line x1="74" x2="246" y1="118" y2="118" stroke={BLOCK} />
      <Line x={74} y={128} w={70} h={6} hot />
      <Line x={74} y={141} w={96} h={4} />
      <Marker x={46} y={80} n={1} />
      <Marker x={46} y={134} n={2} />
      <Marker x={172} y={48} n={3} />
      <Marker x={274} y={150} n={4} />
    </>
  ),
  // Dark trust strip
  strip: (
    <>
      <Chrome />
      <rect x="0" y="16" width="320" height="40" fill={BG} />
      <rect x="0" y="56" width="320" height="64" fill={DARK} />
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <circle cx={22 + i * 78} cy={76} r="6" fill="none" stroke={BRASS} strokeWidth="1.5" />
          <Line x={34 + i * 78} y={72} w={38} h={5} hot={i === 0} />
          <Line x={34 + i * 78} y={84} w={44} h={3} hot={i === 0} />
          <Line x={34 + i * 78} y={91} w={36} h={3} hot={i === 0} />
          <Line x={34 + i * 78} y={98} w={40} h={3} hot={i === 0} />
        </g>
      ))}
      <Marker x={22} y={110} n={1} />
      <Marker x={84} y={66} n={2} />
      <Marker x={88} y={104} n={3} />
    </>
  ),
  // Icon cards
  featureCards: (
    <>
      <Chrome />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <Box x={20 + i * 96} y={44} w={86} h={110} hot={i === 0} />
          <rect x={30 + i * 96} y={54} width={20} height={20} rx="2" fill={i === 0 ? HOT : BLOCK} />
          <Line x={30 + i * 96} y={86} w={56} h={6} hot={i === 0} />
          <Line x={30 + i * 96} y={102} w={66} h={4} />
          <Line x={30 + i * 96} y={111} w={58} h={4} />
          <Line x={30 + i * 96} y={120} w={48} h={4} />
        </g>
      ))}
      <Marker x={60} y={64} n={1} />
      <Marker x={98} y={89} n={2} />
      <Marker x={98} y={114} n={3} />
    </>
  ),
  // Numbered process steps
  steps: (
    <>
      <Chrome />
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <Box x={16 + i * 73} y={40} w={64} h={110} hot={i === 0} />
          <text x={26 + i * 73} y={66} fontSize="16" fontWeight="800" fill={HOT}>
            0{i + 1}
          </text>
          <Line x={26 + i * 73} y={80} w={44} h={6} hot={i === 0} />
          <Line x={26 + i * 73} y={96} w={46} h={4} />
          <Line x={26 + i * 73} y={105} w={40} h={4} />
          <Line x={26 + i * 73} y={114} w={44} h={4} />
        </g>
      ))}
      <Marker x={66} y={60} n={1} />
      <Marker x={84} y={83} n={2} />
      <Marker x={84} y={110} n={3} />
    </>
  ),
  // Numbered factor list on the dark band
  factors: (
    <>
      <Chrome />
      <rect x="0" y="16" width="320" height="164" fill={DARK} />
      <Line x={20} y={34} w={110} h={8} />
      <Line x={20} y={52} w={120} h={4} />
      <Line x={20} y={61} w={100} h={4} />
      <rect x={20} y={80} width={60} height={14} rx="2" fill="#fff" />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <text x={168} y={46 + i * 36} fontSize="11" fontWeight="800" fill={BRASS}>
            0{i + 1}
          </text>
          <Line x={190} y={38 + i * 36} w={70} h={6} hot={i === 0} />
          <Line x={190} y={50 + i * 36} w={100} h={3} />
          <Line x={190} y={57 + i * 36} w={84} h={3} />
          <line x1="164" x2="300" y1={66 + i * 36} y2={66 + i * 36} stroke="#35434a" />
        </g>
      ))}
      <Marker x={160} y={100} n={1} />
      <Marker x={272} y={41} n={2} />
      <Marker x={304} y={56} n={3} />
    </>
  ),
  // Blog card + article
  blogCard: (
    <>
      <Chrome />
      <Box x={18} y={30} w={120} h={136} hot />
      <rect x={19} y={31} width={118} height={54} fill={BLOCK} />
      <Line x={26} y={96} w={40} h={4} hot />
      <Line x={26} y={108} w={100} h={7} hot />
      <Line x={26} y={124} w={104} h={4} />
      <Line x={26} y={133} w={84} h={4} />
      <Line x={26} y={150} w={60} h={3} />
      <Box x={170} y={30} w={132} h={136} />
      <Line x={180} y={42} w={80} h={7} />
      <Line x={180} y={58} w={112} />
      <Line x={180} y={68} w={104} />
      <Line x={180} y={84} w={64} h={6} />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <circle cx={184} cy={102 + i * 11} r="2" fill={HOT} />
          <Line x={192} y={100 + i * 11} w={80} h={4} />
        </g>
      ))}
      <Line x={180} y={140} w={100} />
      <Marker x={78} y={58} n={1} />
      <Marker x={100} y={98} n={2} />
      <Marker x={150} y={112} n={3} />
      <Marker x={290} y={150} n={4} />
    </>
  ),
  // Case study card
  caseStudy: (
    <>
      <Chrome />
      <Box x={18} y={30} w={88} h={136} />
      <Box x={116} y={30} w={88} h={136} hot />
      <Box x={214} y={30} w={88} h={136} />
      <rect x={117} y={31} width={86} height={56} fill={BLOCK} />
      <rect x={122} y={36} width={30} height={9} rx="2" fill={DARK} />
      <Line x={124} y={98} w={66} h={6} hot />
      <Line x={124} y={110} w={50} h={3} />
      <Line x={124} y={120} w={70} h={4} />
      <Line x={124} y={128} w={60} h={4} />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <Line x={124 + i * 26} y={146} w={18} h={6} hot />
          <Line x={124 + i * 26} y={155} w={20} h={3} />
        </g>
      ))}
      <Marker x={160} y={64} n={1} />
      <Marker x={112} y={101} n={2} />
      <Marker x={112} y={123} n={3} />
      <Marker x={208} y={150} n={4} />
    </>
  ),
  // Contact page: details left, map right, floating button
  contact: (
    <>
      <Chrome />
      <Line x={20} y={34} w={110} h={8} hot />
      <Line x={20} y={50} w={120} h={4} />
      <rect x={20} y={62} width={84} height={14} rx="2" fill={HOT} />
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <circle cx={26} cy={92 + i * 14} r="3" fill={HOT} />
          <Line x={36} y={90 + i * 14} w={30} h={4} />
          <Line x={74} y={90 + i * 14} w={56} h={4} />
        </g>
      ))}
      <Box x={150} y={30} w={150} h={112} hot fill={BLOCK} />
      <path d="M225 70 l-8 14 h16 z" fill={HOT} />
      <circle cx={225} cy={70} r="4" fill="#fff" />
      <rect x={20} y={152} width={54} height={14} rx="2" fill={HOT} />
      <Marker x={112} y={69} n={1} />
      <Marker x={138} y={112} n={2} />
      <Marker x={300} y={140} n={3} />
      <Marker x={86} y={159} n={4} />
    </>
  ),
  // Site settings
  redirects: (
    <>
      <rect x="0" y="0" width="320" height="180" rx="6" fill={BG} />
      <Box x={20} y={40} w={125} h={26} />
      <Line x={30} y={50} w={95} h={6} />
      <line x1="30" y1="53" x2="125" y2="53" stroke={DARK} strokeWidth="2" />
      <path d="M152 53 H 172" stroke={HOT} strokeWidth="3" strokeLinecap="round" />
      <path d="M166 46 L 174 53 L 166 60" fill="none" stroke={HOT} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      <Box x={180} y={40} w={120} h={26} hot />
      <Line x={190} y={50} w={90} h={6} hot />
      <Box x={20} y={92} w={280} h={70} fill="#fff" />
      <Line x={34} y={106} w={110} h={5} />
      <Line x={170} y={106} w={110} h={5} hot />
      <Line x={34} y={124} w={90} h={5} />
      <Line x={170} y={124} w={120} h={5} hot />
      <Line x={34} y={142} w={120} h={5} />
      <Line x={170} y={142} w={80} h={5} hot />
      <Marker x={82} y={30} n={1} />
      <Marker x={240} y={30} n={2} />
      <Marker x={300} y={92} n={3} />
    </>
  ),
  settings: (
    <>
      <rect x="0" y="0" width="320" height="180" rx="6" fill="#fff" stroke={BLOCK} />
      <rect x="20" y="18" width="200" height="18" rx="9" fill={BG} stroke={BLOCK} />
      <Line x={20} y={56} w={210} h={8} hot />
      <Line x={20} y={74} w={270} />
      <Line x={20} y={84} w={230} />
      <rect x="0" y="118" width="320" height="62" fill={DARK} />
      <rect x={20} y={132} width={10} height={10} fill="none" stroke="#fff" strokeWidth="1.5" />
      <Line x={36} y={134} w={50} h={5} hot />
      <Line x={20} y={160} w={120} h={4} hot />
      <Marker x={246} y={60} n={1} />
      <Marker x={300} y={80} n={2} />
      <Marker x={160} y={162} n={3} />
    </>
  ),
};

export function GuidePanel({ guide }: { guide: FieldGuide }) {
  return (
    <div className="flex flex-col gap-4 rounded-[6px] border border-brass/50 bg-ivory p-4 sm:flex-row sm:items-center">
      <svg viewBox="0 0 320 180" role="img" aria-label={`Where "${guide.title}" appears on the page`} className="w-full shrink-0 rounded-[4px] border border-line bg-white sm:w-64">
        {DIAGRAMS[guide.diagram] ?? DIAGRAMS.hero}
      </svg>
      <div>
        <p className="font-heading text-sm font-bold text-charcoal">{guide.title}</p>
        <ol className="mt-2 space-y-1.5 text-sm text-ink">
          {guide.steps.map((s, i) => (
            <li key={i} className="flex gap-2">
              <span className="grid size-5 shrink-0 place-items-center rounded-full bg-teal text-[11px] font-bold text-white">{i + 1}</span>
              <span>{s}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
