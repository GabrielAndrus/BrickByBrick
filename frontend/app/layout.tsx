import './globals.css'
import type { Metadata } from 'next'
import { SolanaWalletProvider } from './components/SolanaWalletProvider'

export const metadata: Metadata = {
  title: 'Building Blocks',
  description: 'Rebuild your identity, piece by piece',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>
        <SolanaWalletProvider>{children}</SolanaWalletProvider>
      </body>
    </html>
  )
}
