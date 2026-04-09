import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

Deno.serve(async (req) => {
  try {
    const { noteId, password } = await req.json()
    if (!noteId || !password) {
      return new Response('missing noteId or password', { status: 400 })
    }

    if (password !== Deno.env.get('DELETE_PASSWORD')) {
      return new Response('wrong password', { status: 401 })
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    )

    const { error } = await supabase.from('guestbook_notes').delete().eq('id', noteId)
    if (error) return new Response(error.message, { status: 500 })

    return new Response('ok', { status: 200 })
  } catch (err) {
    return new Response(err instanceof Error ? err.message : 'unknown error', { status: 500 })
  }
})
