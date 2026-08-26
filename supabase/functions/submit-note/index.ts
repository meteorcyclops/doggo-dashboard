import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const allowedOrigins = new Set([
  'https://dog.xuan.tw',
  'http://127.0.0.1:4173',
  'http://localhost:4173',
])

function corsHeaders(req: Request) {
  const origin = req.headers.get('origin') || ''
  return {
    'Access-Control-Allow-Origin': allowedOrigins.has(origin) ? origin : 'https://dog.xuan.tw',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Vary': 'Origin',
  }
}

function cleanText(value: unknown) {
  return String(value || '').replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').trim()
}

async function clientHash(req: Request) {
  const address = req.headers.get('cf-connecting-ip')
    || req.headers.get('x-forwarded-for')?.split(',')[0]?.trim()
    || 'unknown'
  const salt = Deno.env.get('RATE_LIMIT_SALT') || 'doggo-guestbook-v1'
  const bytes = new TextEncoder().encode(`${salt}:${address}`)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, '0')).join('')
}

Deno.serve(async (req) => {
  const headers = corsHeaders(req)
  const origin = req.headers.get('origin') || ''
  if (origin && !allowedOrigins.has(origin)) return new Response('request rejected', { status: 403, headers })
  if (req.method === 'OPTIONS') return new Response('ok', { headers })
  if (req.method !== 'POST') return new Response('method not allowed', { status: 405, headers })

  try {
    const body = await req.json()
    const nickname = cleanText(body?.nickname) || '匿名訪客'
    const message = cleanText(body?.message)
    if (nickname.length > 24 || message.length < 1 || message.length > 220) {
      return new Response('invalid input', { status: 400, headers })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    )
    await supabase.from('guestbook_rate_limits').delete().lt('created_at', new Date(Date.now() - 3_600_000).toISOString())
    const hash = await clientHash(req)
    const bucketMs = 30_000
    const windowStart = new Date(Math.floor(Date.now() / bucketMs) * bucketMs).toISOString()
    const { error: rateError } = await supabase.from('guestbook_rate_limits').insert({
      client_hash: hash,
      action: 'submit',
      window_start: windowStart,
    })
    if (rateError) return new Response('please retry later', { status: 429, headers })

    const { error } = await supabase.from('guestbook_notes').insert({ nickname, message })
    if (error) return new Response('unable to save note', { status: 500, headers })

    const resendKey = Deno.env.get('RESEND_API_KEY')
    const notifyTo = Deno.env.get('NOTIFY_EMAIL_TO')
    const notifyFrom = Deno.env.get('NOTIFY_EMAIL_FROM')
    if (Deno.env.get('ENABLE_GUESTBOOK_EMAIL') === 'true' && resendKey && notifyTo && notifyFrom) {
      try {
        await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${resendKey}` },
          body: JSON.stringify({
            from: notifyFrom,
            to: [notifyTo],
            subject: `${nickname.replace(/[\r\n]/g, ' ')} 在狗狗情報小屋留言`,
            text: message,
          }),
        })
      } catch {
        // Saving the note remains successful if the optional notification is unavailable.
      }
    }

    return new Response('ok', { status: 201, headers })
  } catch {
    return new Response('unable to save note', { status: 500, headers })
  }
})
