// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §6.3, §10.1 (waktu ISO 8601 UTC); PRD §9.10

// Satu-satunya formatter waktu Console: API memakai UTC (SA), jadi tampilan tetap UTC dengan akhiran "UTC"; null menjadi "-".
export function formatUtcTimestamp(isoValue: string | null): string {
  if (!isoValue) {
    return "-";
  }
  const parsed = new Date(isoValue);
  if (Number.isNaN(parsed.getTime())) {
    return isoValue;
  }
  return (
    new Intl.DateTimeFormat("id-ID", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    }).format(parsed) + " UTC"
  );
}
