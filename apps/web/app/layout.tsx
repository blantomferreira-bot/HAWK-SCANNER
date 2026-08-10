import type { Metadata } from "next";
import { ForceFullNavigation } from "@/components/force-full-navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: "HAWK SCANNER | Inteligência quantitativa cripto",
  description: "Plataforma de inteligência quantitativa para priorizar investigação de ativos digitais.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR" className="dark scroll-smooth"><body><ForceFullNavigation />{children}</body></html>;
}
