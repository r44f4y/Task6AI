export async function api<T>(path:string, method='GET', data?:unknown):Promise<T> {
  const body = data instanceof FormData ? data : data === undefined ? undefined : JSON.stringify(data)
  const response = await fetch('/api'+path,{method,body,headers:typeof body==='string' ? {'Content-Type':'application/json'} : undefined})
  if (!response.ok) {
    const error = await response.json().catch(()=>({detail:response.statusText}))
    throw new Error(Array.isArray(error.detail) ? error.detail.map((item:{msg:string})=>item.msg).join('; ') : error.detail)
  }
  if (response.headers.get('Content-Type')?.includes('application/zip')) return await response.blob() as T
  return await response.json() as T
}
export function localDate(date:string,withTime=false) {
  return new Intl.DateTimeFormat('en-CA',{month:'short',day:'numeric',
    ...(withTime ? {hour:'numeric',minute:'2-digit'} : {})}).format(new Date(date))
}
export const label=(value:string)=>value.toLowerCase().replaceAll('_',' ').replace(/^./,ch=>ch.toUpperCase())
export const modeName=(value:string)=>value==='local_ai' ? 'Local AI' : 'Offline demo'
export function saveBlob(blob:Blob,name:string) {
  const url=URL.createObjectURL(blob)
  const a=document.createElement('a')
  a.href=url
  a.download=name
  a.click()
  window.setTimeout(()=>URL.revokeObjectURL(url),1000)
}
