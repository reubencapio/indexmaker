import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { LineChart } from 'lucide-react'

const LAST_UPDATED = '11 October 2026'
const CONTACT_EMAIL = 'support@indexmaker.ai'

type Section = { heading: string; body: React.ReactNode }

const contact = (
  <>
    Write to <a className="underline" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> or use the{' '}
    <Link className="underline" to="/contact">contact form</Link>.
  </>
)

const TERMS: Section[] = [
  {
    heading: 'The service',
    body: (
      <p>
        IndexMaker lets you design rules-based stock indices, test them against historical prices, track
        them over time and share them. By creating an account or using the site you agree to these terms.
      </p>
    ),
  },
  {
    heading: 'Not investment advice',
    body: (
      <>
        <p>
          IndexMaker is a research and information tool. Nothing on the site, in a report, in an email or
          produced by the AI index builder is investment, financial, tax or legal advice, or a recommendation
          to buy or sell any security.
        </p>
        <p>
          Backtests and performance figures are hypothetical. They are calculated from historical prices
          using the rules or constituents you chose, do not reflect real trading, and say nothing reliable
          about future results. An index on IndexMaker is not a fund and cannot be invested in directly. You
          are responsible for your own investment decisions.
        </p>
      </>
    ),
  },
  {
    heading: 'Market data',
    body: (
      <p>
        Prices and company data come from third-party sources and can be delayed, incomplete or wrong. We do
        not guarantee their accuracy. Check any figure you intend to rely on against an authoritative source.
      </p>
    ),
  },
  {
    heading: 'Your account',
    body: (
      <p>
        Keep your password private and tell us if you think someone else has used your account. You are
        responsible for what happens under it. You must be at least 18 to use the service.
      </p>
    ),
  },
  {
    heading: 'Plans and payment',
    body: (
      <>
        <p>
          The Free plan costs nothing. Paid plans are billed in advance, monthly or yearly, through Stripe,
          and renew automatically until you cancel. Prices are shown on the pricing page before you pay.
        </p>
        <p>
          You can cancel at any time from Settings. Cancelling stops the next renewal; you keep the paid
          features until the end of the period you have paid for. Refunds are covered by the{' '}
          <Link className="underline" to="/refunds">refund policy</Link>. If a payment fails we will ask you to
          update your card, and the account returns to the Free plan if it is not resolved.
        </p>
      </>
    ),
  },
  {
    heading: 'Your content',
    body: (
      <p>
        The indices, rules and data you create or upload remain yours. You give us permission to store and
        process them to run the service for you. When you publish a share link or an embed, the content you
        chose to show is public to anyone with the link until you switch it off.
      </p>
    ),
  },
  {
    heading: 'Acceptable use',
    body: (
      <p>
        Do not use the service to break the law, to send unsolicited email, to misrepresent hypothetical
        performance as real, to scrape or overload the site, or to try to access other people's accounts or
        data. We may suspend an account that does.
      </p>
    ),
  },
  {
    heading: 'Availability and liability',
    body: (
      <p>
        The service is provided as it is, without warranties. We work to keep it running and correct but do
        not promise it will be uninterrupted or error-free. To the extent the law allows, we are not liable
        for investment losses or for indirect or consequential loss, and our total liability to you is limited
        to the amount you paid us in the twelve months before the claim.
      </p>
    ),
  },
  {
    heading: 'Changes and closing your account',
    body: (
      <p>
        We may update these terms; if a change is significant we will tell you by email or in the app before
        it takes effect. You can stop using the service and ask us to delete your account at any time.
      </p>
    ),
  },
  { heading: 'Contact', body: <p>{contact}</p> },
]

const PRIVACY: Section[] = [
  {
    heading: 'What we collect',
    body: (
      <ul className="list-disc space-y-1 pl-5">
        <li>Account details: your email address, your name if you give it, and a hashed password.</li>
        <li>What you create: indices, rules, backtests, reports, uploaded data and delivery settings.</li>
        <li>
          Billing details: your plan and subscription status. Card details are entered on Stripe's pages and
          never reach our servers.
        </li>
        <li>
          Follower emails: if you follow a public index, we keep your email address for that purpose only.
        </li>
        <li>Technical logs: IP address and request details, kept for security and troubleshooting.</li>
      </ul>
    ),
  },
  {
    heading: 'How we use it',
    body: (
      <p>
        To run the service: signing you in, calculating and storing your indices, taking payment, sending the
        emails you asked for (password resets, team invitations, scheduled reports, index updates you follow)
        and keeping the site secure. We do not sell personal data and we do not use it for advertising.
      </p>
    ),
  },
  {
    heading: 'Who processes it for us',
    body: (
      <>
        <p>We share data only with the providers needed to operate the service:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Stripe, for payments and billing.</li>
          <li>Koyeb, Vercel and Supabase, for hosting the application and its database.</li>
          <li>
            Anthropic and Google, whose AI models turn the description you type into an index. The text of
            that description is sent to them; your account details are not.
          </li>
          <li>Our email provider, to deliver messages to you.</li>
        </ul>
      </>
    ),
  },
  {
    heading: 'Cookies and browser storage',
    body: (
      <p>
        We store your sign-in session in your browser so you stay logged in. We do not use advertising or
        analytics trackers. Stripe may set its own cookies on its checkout and billing pages.
      </p>
    ),
  },
  {
    heading: 'How long we keep it',
    body: (
      <p>
        We keep your account and content for as long as the account is open. If you ask us to delete your
        account we delete it and its content, except records we must keep for tax and accounting. A follower
        email is deleted as soon as that person unsubscribes.
      </p>
    ),
  },
  {
    heading: 'Your rights',
    body: (
      <p>
        You can ask for a copy of your personal data, ask us to correct or delete it, or object to how we use
        it. {contact} We will reply within 30 days.
      </p>
    ),
  },
  {
    heading: 'Changes',
    body: <p>If we change this policy in a way that matters, we will tell you by email or in the app.</p>,
  },
]

const REFUNDS: Section[] = [
  {
    heading: 'Cancelling',
    body: (
      <p>
        Cancel at any time from Settings, under "Manage billing". You will not be charged again, and you keep
        your paid features until the end of the period you have already paid for. After that the account
        moves to the Free plan; your indices are kept.
      </p>
    ),
  },
  {
    heading: 'Refunds',
    body: (
      <>
        <p>
          If a paid plan is not right for you, ask within 14 days of your first payment and we will refund it
          in full.
        </p>
        <p>
          After that, payments are not refunded for the remainder of a period, including on yearly plans, but
          you can still cancel to stop future charges. If you were charged in error, or twice, tell us and we
          will put it right.
        </p>
      </>
    ),
  },
  {
    heading: 'How to ask',
    body: (
      <p>
        {contact} Use the email address on your account. Refunds go back to the original payment method and
        usually arrive within 5 to 10 business days.
      </p>
    ),
  },
]

const DOCUMENTS = {
  terms: { title: 'Terms of Service', sections: TERMS },
  privacy: { title: 'Privacy Policy', sections: PRIVACY },
  refunds: { title: 'Refund Policy', sections: REFUNDS },
} as const

export type LegalDocument = keyof typeof DOCUMENTS

export const LEGAL_LINKS: Array<{ to: string; label: string }> = [
  { to: '/terms', label: 'Terms' },
  { to: '/privacy', label: 'Privacy' },
  { to: '/refunds', label: 'Refunds' },
]

/** Terms, privacy and refund pages. Public, and linked from the footer and sign-up. */
export function LegalPage({ document: name }: { document: LegalDocument }) {
  const doc = DOCUMENTS[name]

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [name])

  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b">
        <div className="container mx-auto flex items-center justify-between px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <LineChart className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">IndexMaker</span>
          </Link>
          <div className="flex gap-4 text-sm text-muted-foreground">
            {LEGAL_LINKS.map((link) => (
              <Link key={link.to} to={link.to} className="hover:text-foreground">
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      <main className="container mx-auto max-w-3xl px-4 py-12 sm:px-6">
        <h1 className="text-3xl font-bold">{doc.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Last updated {LAST_UPDATED}</p>

        <div className="mt-8 space-y-8">
          {doc.sections.map((section) => (
            <section key={section.heading}>
              <h2 className="mb-2 text-lg font-semibold">{section.heading}</h2>
              <div className="space-y-3 leading-relaxed text-muted-foreground">{section.body}</div>
            </section>
          ))}
        </div>
      </main>
    </div>
  )
}
