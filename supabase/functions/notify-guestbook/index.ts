Deno.serve(() => new Response('deprecated', {
  status: 410,
  headers: { 'Access-Control-Allow-Origin': 'https://dog.xuan.tw', 'Vary': 'Origin' },
}))
