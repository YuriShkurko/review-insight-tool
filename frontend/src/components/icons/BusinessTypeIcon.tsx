import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { businessType?: string | null };

const COMMON: SVGProps<SVGSVGElement> = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

function BarIcon(props: SVGProps<SVGSVGElement>) {
  // Beer mug.
  return (
    <svg {...COMMON} {...props}>
      <path d="M6 4h9v15a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4Z" />
      <path d="M15 8h2.5a2.5 2.5 0 0 1 0 5H15" />
      <path d="M9 8v9M12 8v9" />
    </svg>
  );
}

function RestaurantIcon(props: SVGProps<SVGSVGElement>) {
  // Fork & knife.
  return (
    <svg {...COMMON} {...props}>
      <path d="M7 3v8a2 2 0 0 0 2 2v8" />
      <path d="M5 3v6M9 3v6" />
      <path d="M16 3c-1.5 1.5-2 3-2 5s.5 2.5 2 3v10" />
    </svg>
  );
}

function CafeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...COMMON} {...props}>
      <path d="M5 8h12v6a4 4 0 0 1-4 4H9a4 4 0 0 1-4-4V8Z" />
      <path d="M17 10h2a2 2 0 0 1 0 4h-2" />
      <path d="M8 3c0 1 1 1 1 2s-1 1-1 2M12 3c0 1 1 1 1 2s-1 1-1 2" />
    </svg>
  );
}

function GymIcon(props: SVGProps<SVGSVGElement>) {
  // Dumbbell.
  return (
    <svg {...COMMON} {...props}>
      <path d="M3 9v6M6 7v10M18 7v10M21 9v6" />
      <path d="M6 12h12" />
    </svg>
  );
}

function HotelIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...COMMON} {...props}>
      <path d="M3 21V8l9-5 9 5v13" />
      <path d="M9 21v-6h6v6" />
    </svg>
  );
}

function ClinicIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...COMMON} {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M12 8v8M8 12h8" />
    </svg>
  );
}

function SalonIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...COMMON} {...props}>
      <circle cx="6" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <path d="M9 8l11 11M9 16l11-11" />
    </svg>
  );
}

function RetailIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...COMMON} {...props}>
      <path d="M3 8h18l-1.5 11a2 2 0 0 1-2 2h-11a2 2 0 0 1-2-2L3 8Z" />
      <path d="M9 8V5a3 3 0 0 1 6 0v3" />
    </svg>
  );
}

function StoreIcon(props: SVGProps<SVGSVGElement>) {
  // Generic building / fallback.
  return (
    <svg {...COMMON} {...props}>
      <path d="M4 9l1.5-4h13L20 9" />
      <path d="M4 9v11h16V9" />
      <path d="M9 20v-6h6v6" />
    </svg>
  );
}

export function BusinessTypeIcon({ businessType, ...rest }: IconProps) {
  const t = (businessType ?? "").toLowerCase();
  switch (t) {
    case "bar":
      return <BarIcon {...rest} />;
    case "restaurant":
      return <RestaurantIcon {...rest} />;
    case "cafe":
      return <CafeIcon {...rest} />;
    case "gym":
      return <GymIcon {...rest} />;
    case "hotel":
      return <HotelIcon {...rest} />;
    case "clinic":
      return <ClinicIcon {...rest} />;
    case "salon":
      return <SalonIcon {...rest} />;
    case "retail":
      return <RetailIcon {...rest} />;
    default:
      return <StoreIcon {...rest} />;
  }
}
