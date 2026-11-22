import { expect, test, type Page } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

async function capture(page:Page,name:string){
  if(process.env.RELAY_CAPTURE_SCREENSHOTS!=='1')return
  const location=new URL('../../docs/images/',import.meta.url)
  mkdirSync(fileURLToPath(location),{recursive:true})
  await page.screenshot({path:fileURLToPath(new URL(name+'.png',location)),animations:'disabled'})
}

async function scenario(page:Page,title:string){
  await page.getByRole('navigation').getByRole('button',{name:'Demo Scenarios'}).click()
  const card=page.locator('.scenario').filter({has:page.getByRole('heading',{name:title,exact:true})})
  await card.getByRole('button',{name:'Open scenario'}).click()
  await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible()
}

test.beforeEach(async({page})=>{
  await page.route('**/*',route=>{
    const url=new URL(route.request().url())
    if(url.hostname==='127.0.0.1')return route.continue()
    return route.abort('internetdisconnected')
  })
  await page.goto('/')
  await expect(page.getByRole('heading',{name:'Workflow overview'})).toBeVisible()
  await expect(page.getByRole('button',{name:'Offline demo'})).toBeVisible()
})

test('dispatcher handles an ambiguous appointment through download',async({page})=>{
  await capture(page,'relay-overview')
  await scenario(page,'Appointment at “8”')
  await page.getByRole('button',{name:'Process request'}).click()
  await expect(page.getByText('Ambiguous time. Confirm AM or PM.')).toBeVisible()
  await expect(page.getByRole('button',{name:'Approve request',exact:true})).toBeDisabled()
  await page.getByRole('button',{name:'Generate follow-up',exact:true}).click()
  await expect(page.getByRole('textbox',{name:'Clarification draft'})).toHaveValue(/Confirm AM or PM/)
  if(process.env.RELAY_CAPTURE_SCREENSHOTS==='1')await page.getByRole('button',{name:'Appointment time',exact:true}).click()
  await capture(page,'relay-request-workspace')
  await page.getByRole('button',{name:'Approve message',exact:true}).click()
  await page.getByRole('button',{name:'Simulate send',exact:true}).click()
  await page.getByRole('button',{name:'Simulate customer reply',exact:true}).click()
  await page.getByRole('button',{name:'Process request'}).click()
  await expect(page.getByText('All required checks passed.')).toBeVisible()
  await expect(page.getByText('Original wording · 8 in the morning')).toBeAttached()
  await page.getByRole('button',{name:'Generate output'}).click()
  await expect(page.getByRole('heading',{name:'Transport order'})).toBeVisible()
  await page.getByRole('button',{name:'Approve request',exact:true}).click()
  await page.getByRole('dialog').getByRole('button',{name:'Confirm'}).click()
  await page.getByRole('button',{name:'Export approved record'}).click()
  const download=page.waitForEvent('download')
  await page.getByRole('button',{name:'Export ZIP'}).click()
  expect((await download).suggestedFilename()).toMatch(/^relay-.*\.zip$/)
  await expect(page.getByText('Approved package saved locally and downloaded.')).toBeVisible()
})

test('switch to accommodations and edit the staff plan',async({page})=>{
  await scenario(page,'Low vision in customer support')
  await expect(page.getByRole('combobox',{name:'Organisation'})).toHaveValue('enabled_talent')
  await page.getByRole('button',{name:'Process request'}).click()
  await page.getByRole('button',{name:'Generate output'}).click()
  await expect(page.getByRole('heading',{name:'Workplace accommodation plan'})).toBeVisible()
  await page.getByRole('button',{name:'Edit plan text'}).click()
  await page.getByRole('textbox',{name:'Staff-reviewed plan'}).fill('Staff confirmed magnification testing and a first-week check-in.')
  await page.getByRole('button',{name:'Confirm'}).click()
  await expect(page.getByText('Staff confirmed magnification testing and a first-week check-in.')).toBeVisible()
  await page.getByRole('button',{name:'Approve request',exact:true}).click()
  await page.getByRole('dialog').getByRole('button',{name:'Confirm'}).click()
  await expect(page.getByText('Approved',{exact:true})).toBeVisible()
})

test('save, load and use a new workflow from the builder',async({page})=>{
  await page.getByRole('navigation').getByRole('button',{name:'Workflow Builder'}).click()
  await page.getByRole('button',{name:'New organisation'}).click()
  await page.getByLabel('Organisation name').fill('Demo Kayak Repairs')
  await page.getByLabel('Workflow name').fill('Kayak repairs')
  await page.getByLabel('Industry').fill('Equipment repair')
  await page.getByLabel('Approval role').fill('Service reviewer')
  await page.getByLabel('Field label',{exact:true}).fill('Kayak model')
  await page.getByRole('button',{name:'Save workflow'}).click()
  await expect(page.getByRole('combobox',{name:'Organisation',exact:true}).first()).toHaveValue('demo_kayak_repairs')
  await page.getByRole('button',{name:'Version 1 Current version'}).click()
  await expect(page.getByLabel('Field label',{exact:true})).toHaveValue('Kayak model')
  await page.getByLabel('Example request').fill('Kayak model: Fictional Delta')
  await page.getByRole('button',{name:'Process example'}).click()
  await expect(page.getByRole('heading',{name:'Workflow Builder example'})).toBeVisible()
  await expect(page.locator('.field-value').getByText('Fictional Delta',{exact:true})).toBeVisible()
  await expect(page.getByText('All required checks passed.')).toBeVisible()
})

test('mobile navigation and readable offline indicator',async({page})=>{
  await page.setViewportSize({width:390,height:844})
  await page.getByRole('button',{name:'Open navigation'}).click()
  await page.getByRole('navigation').getByRole('button',{name:'Unified Inbox'}).click()
  await expect(page.getByRole('heading',{name:'Unified Inbox'})).toBeVisible()
  await expect(page.getByRole('button',{name:'Offline demo'})).toBeVisible()
  expect(await page.locator('body').evaluate(node=>node.scrollWidth)).toBeLessThanOrEqual(390)
})

test('owner can inspect a real synthetic flyer and reviewed pricing',async({page})=>{
  await scenario(page,'Flyer sizes and pricing')
  await page.getByRole('button',{name:'Attachments'}).click()
  const artwork=page.getByRole('img',{name:'Design preview for event-1.png'})
  await expect(artwork).toBeVisible()
  await expect.poll(()=>artwork.evaluate((img:HTMLImageElement)=>img.naturalWidth)).toBeGreaterThan(1000)
  await page.getByRole('button',{name:'Process request'}).click()
  await expect(page.getByText('Provide flyer size.')).toBeVisible()
  await page.getByRole('button',{name:'Generate follow-up',exact:true}).click()
  await expect(page.getByRole('textbox',{name:'Clarification draft'})).toHaveValue(/Synthetic demo pricing/)
})
