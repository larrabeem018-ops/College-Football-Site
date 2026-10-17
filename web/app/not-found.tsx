import Link from "next/link";
export default function NotFound() {
  return (
    <div className="flex flex-col items-start gap-4 py-16">
      <div className="eyebrow text-accent">404</div>
      <h1 className="display m-0 text-[56px] leading-none">Fumble.</h1>
      <p className="m-0 text-soft">That page doesn&apos;t exist, or last week&apos;s game page has rotated out.</p>
      <Link href="/" className="inline-flex h-12 items-center rounded-xl bg-accent px-5 font-bold text-[#06120B] hover:text-[#06120B]">Back to this week</Link>
    </div>
  );
}
