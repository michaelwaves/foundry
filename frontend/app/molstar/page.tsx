import MolstarViewer from "@/components/molstar-viewer";

export default async function MolstarPage({ searchParams }: { searchParams: Promise<{ url?: string }> }) {
    const { url = "https://files.rcsb.org/download/1CRN.cif" } = await searchParams;
    return <MolstarViewer url={url} />;
}
