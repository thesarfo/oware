interface Props {
  className?: string;
  showBuildTag?: boolean;
}

export function Footer({ className = "", showBuildTag = true }: Props) {
  return (
    <div
      className={`flex flex-wrap items-center justify-center gap-3 font-mono text-[10px] uppercase tracking-wider text-muted dark:text-dark-muted ${className}`}
    >
      <span>
        made by{" "}
        <a
          href="https://github.com/blackprince001"
          target="_blank"
          rel="noreferrer"
          className="underline decoration-line/60 underline-offset-2 transition-colors hover:text-ink hover:decoration-ink dark:hover:text-dark-ink"
        >
          @blackprince001
        </a>
      </span>
      <span aria-hidden="true">·</span>
      <a
        href="https://blackprince001.github.io/"
        target="_blank"
        rel="noreferrer"
        className="underline decoration-line/60 underline-offset-2 transition-colors hover:text-ink hover:decoration-ink dark:hover:text-dark-ink"
      >
        blackprince001.github.io
      </a>
      {showBuildTag && (
        <>
          <span aria-hidden="true">·</span>
          <span>development build</span>
        </>
      )}
    </div>
  );
}
