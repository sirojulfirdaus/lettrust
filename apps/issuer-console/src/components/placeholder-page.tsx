// Owner: Van (PIC 2) | Status: COMPLETE | Ref: SA §11.2.1
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";

type PlaceholderPageProps = {
  title: string;
  owner: string;
  refs: string[];
  checklist: string[];
};

// Kerangka halaman yang belum diimplementasikan beserta daftar periksa untuk pemilik modul.
export function PlaceholderPage({ title, owner, refs, checklist }: PlaceholderPageProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold">{title}</h1>
          <Badge variant="secondary">Placeholder — belum diimplementasikan</Badge>
        </div>
        <CardDescription>
          Pemilik: {owner} · Referensi: {refs.join(", ")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <h2 className="mb-2 font-semibold">Daftar periksa implementasi</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm">
          {checklist.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
