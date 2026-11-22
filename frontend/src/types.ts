export type Value = string | number | boolean | null
export type Mode = 'local_ai' | 'offline_demo'
export type FieldType = 'text'|'number'|'currency'|'date'|'time'|'boolean'|'email'|'phone'|'address'|'select'
export type FieldSpec = { key: string; label: string; type: FieldType; required: boolean; when?: {field:string;equals:Value}|null; options: string[]; minimum?: number|null; maximum?: number|null; integer?: boolean }
export type Workflow = {
  id: string; name: string; title: string; industry: string; channels: string[]; description: string
  reviewer: string; output: string; fields: FieldSpec[]; clarification?:string; template?:string
  version: number; adapter?:string|null
}
export type Evidence = { source: string; label: string; page: number|null; quote: string; value: Value; raw:string; mode:Mode; origin?:string }
export type Fact= { status:string; value:Value; raw:Value; reason?:string; evidence:Evidence[]; history:{raw:Value;value:Value;status:string}[] }
export type Issue = { key:string; label:string; kind:string; detail:string }
export type Message = { id:string; external_id:string; sender:string; created:string; body:string; direction:string; in_reply_to:string|null; historical:boolean }
export type DocumentSource = { id:string; filename:string; kind:string; created:string; version:number; warning:string|null; pages:{page:number|null;text:string}[] }
export type Audit = {at:string;kind:string;detail:string;subject?:string;id?:string;mode?:Mode;revision?:number}
export type Approval = {at:string;role:string;comment:string;decision:string;revision:number;active:boolean}
export type Output = { title:string; summary:string; sections:Record<string,string>; values:Record<string,Value>; calculation:Record<string,Value>; revision:number; staff_edit?:string; format:string }
export type Draft = { id:string; edit_version?:number; text:string; mode:Mode; status:'draft'|'approved'|'sent'; reply_received?:boolean }
export type CaseSummary = {id:string;org:string;subject:string;sender:string;channel:string;version:number;thread:string;created:string;updated:string;status:string;reviewer:string;unread:boolean;required:number;resolved:number;revision:number;fixture:string|null;processing_error:string|null}
export type CaseDetail = CaseSummary & {
  workflow:Workflow; fields:Record<string,Fact>; issues:Issue[]; messages:Message[]; attachments:DocumentSource[]
  audit:Audit[]; approvals:Approval[]; reply_available:boolean; reply_without_draft:boolean; duplicate_available:boolean
  state:{draft:Draft|null;output:Output|null;output_history:Output[];processed:string[];exports:{path:string;at:string}[];runs:Run[]}
}
export type Run = {at:string;mode:Mode;elapsed_ms?:number;success:boolean;facts?:number}
export type Metrics = {total:number;status:Record<string,number>;missing:Record<string,number>;volume:Record<string,number>;completeness:number;processed:number;runs:Run[];average_ms:number|null;activity:Audit[]}
export type Scenario = {id:string;org:string;title:string;missing:string[];ambiguous:string[];conflict:string|null;unsupported:boolean;case_id:string;replies:number}
export type Health = {mode:Mode;model:string;available:boolean;ready:boolean;models:string[]}
