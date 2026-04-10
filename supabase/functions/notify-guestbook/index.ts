const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })

  try {
    const { nickname, message, createdAt } = await req.json()
    if (!nickname || !message) {
      return new Response('missing nickname or message', { status: 400, headers: corsHeaders })
    }

    const resendKey = Deno.env.get('RESEND_API_KEY')
    const notifyTo = Deno.env.get('NOTIFY_EMAIL_TO')
    const notifyFrom = Deno.env.get('NOTIFY_EMAIL_FROM')
    if (!resendKey) {
      return new Response('missing RESEND_API_KEY', { status: 500, headers: corsHeaders })
    }
    if (!notifyTo || !notifyFrom) {
      return new Response('missing NOTIFY_EMAIL_TO or NOTIFY_EMAIL_FROM', { status: 500, headers: corsHeaders })
    }

    const subject = 'Doggo Dashboard 有新留言'
    const text = `狗狗留言板有新便條紙\n\n來自：${nickname}\n內容：${message}${createdAt ? `\n時間：${createdAt}` : ''}`

    const resp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${resendKey}`,
      },
      body: JSON.stringify({
        from: notifyFrom,
        to: [notifyTo],
        subject,
        text,
      }),
    })

    if (!resp.ok) {
      const detail = await resp.text()
      return new Response(`email notify failed: ${resp.status} ${detail}`, { status: 500, headers: corsHeaders })
    }

    return new Response('ok', { status: 200, headers: corsHeaders })
  } catch (err) {
    return new Response(err instanceof Error ? err.message : 'unknown error', { status: 500, headers: corsHeaders })
  }
})
