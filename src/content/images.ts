/**
 * Photography register.
 * ------------------------------------------------------------------
 * Images are served from Unsplash (free licence, hotlinking permitted)
 * as realistic development photography. Replace any entry with the
 * company's own photography by pointing `src` at a file in /public.
 *
 * Every image is used once. Alt text describes the photograph itself.
 */
export type ImageKey =
  | "hero"
  | "intro"
  | "upvc"
  | "aluminium"
  | "timber"
  | "sash"
  | "tilt"
  | "glazing"
  | "handles"
  | "hinges"
  | "glass"
  | "seals"
  | "frames"
  | "commercial"
  | "doorlocks"
  | "doorhinges"
  | "about"
  | "workshop"
  | "commercialExterior"
  | "areas";

export type SiteImage = { src: string; alt: string; width: number; height: number };

const unsplash = (id: string, w: number, h: number) =>
  `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=${w}&h=${h}&q=80`;

const img = (id: string, alt: string, width = 1200, height = 800): SiteImage => ({
  src: unsplash(id, width, height),
  alt,
  width,
  height,
});

export const images: Record<ImageKey, SiteImage> = {
  hero: img(
    "1504615755583-2916b52192a3",
    "Terrace of period London houses with painted timber sash windows and a black front door",
    1200,
    1400,
  ),
  intro: img("1621905251189-08b45d6a269e", "Repair specialist in a hard hat and gloves working on a fixture with a screwdriver", 1200, 900),
  upvc: img("1503594384566-461fe158e797", "White uPVC casement windows on the gable of a rendered house"),
  aluminium: img("1600047509782-20d39509f26d", "Modern white house with dark grey aluminium framed windows"),
  timber: img("1589939705384-5185137a7f0f", "Carpenter working on a length of timber with a cordless drill"),
  sash: img("1616137466211-f939a420be84", "Living room with three tall traditional sash windows"),
  tilt: img("1522708323590-d24dbb6b0267", "Apartment interior with white framed opening windows"),
  glazing: img("1501183638710-841dd1904471", "Open-plan living space with large double-glazed windows"),
  handles: img("1530124566582-a618bc2615dc", "Tool bag holding pliers, screwdrivers and hand tools used for window hardware"),
  hinges: img("1572981779307-38b8cabb2407", "Cordless drill driver on a white surface"),
  glass: img("1493809842364-78817add7ffb", "Bright white framed window letting daylight into a living room"),
  seals: img("1505691938895-1758d7feb511", "Pair of white windows in a light sitting room"),
  frames: img("1600210491892-03d54c0aaf87", "Living room with arched black framed windows"),
  commercial: img("1497366216548-37526070297c", "Office interior with floor-to-ceiling glass partitions and windows"),
  doorlocks: img("1558618666-fcd25c85cd64", "Specialist wearing a head torch working on a brass lock cylinder"),
  doorhinges: img("1581783898377-1c85bf937427", "Screwdriver, pliers, fixings and brush laid out on a white bench"),
  about: img("1600121848594-d8644e57abab", "Bay window in a traditional London living room", 1200, 900),
  workshop: img("1426927308491-6380b6a9936f", "Wall of hand tools in a joinery workshop", 1200, 900),
  commercialExterior: img("1486406146926-c627a92ad1ab", "Glass office buildings seen from street level", 1200, 900),
  areas: img("1448630360428-65456885c650", "Brick apartment block with modern windows against a blue sky", 1200, 900),
};
