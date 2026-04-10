import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

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

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    )

    const target = Deno.env.get('LINE_TARGET')
    if (!target) {
      return new Response('missing LINE_TARGET', { status: 500, headers: corsHeaders })
    }

    const text = `狗狗留言板有新便條紙\n\n${nickname}\n${message}\n\n${createdAt || ''}`.trim()

    const { error } = await supabase.functions.invoke('line-notify-proxy', {
      body: { target, message: text },
    })

    if (error) return new Response(error.message, { status: 500, headers: corsHeaders })
    return new Response('ok', { status: 200, headers: corsHeaders })
  } catch (err) {
    return new Response(err instanceof Error ? err.message : 'unknown error', { status: 500, headers: corsHeaders })
  }
})
