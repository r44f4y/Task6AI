from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = {'A5':(148,210),'A6':(105,148)}

def money(number):
    return format(number.quantize(Decimal('0.01'),rounding=ROUND_HALF_UP),'f')

def printing_reference(workflow):
    prices = workflow['prices']
    return ("Synthetic demo pricing (CAD): A5 (148 × 210 mm) at $" + prices['A5'] +
            " each or A6 (105 × 148 mm) at $" + prices['A6'] +
            " each. Double-sided adds $" + prices['double_sided'] +
            " per flyer. Black and white subtracts $" + prices['black_and_white_discount'] +
            " per flyer. Design files: PDF or PNG, 300 DPI or higher.")

def checks(workflow, values, conversation, attachment_names=()):
    adapter = workflow.get('adapter')
    results=[]
    def issue(key, label, detail):
        results.append(dict(key=key,label=label,detail=detail,kind="INVALID"))
    if adapter=='transport':
        import re
        opening = conversation[0]['body'].split('\n\n',1)[0] if conversation else ''
        if re.search(r'\b(cancel(?:lation)?|rush load|change (?:the|an) existing order)\b',opening,re.I):
            issue('__scope','Manual handling','Changes, cancellations and rush loads require dispatch handling outside this workflow.')
    if adapter=='print' and values.get('design'):
        from backend.files import safe_name
        if safe_name(values['design']).casefold() not in {name.casefold() for name in attachment_names}:
            issue('design','Design file','Attach the artwork so the owner can review the actual design.')
    if adapter=='print' and values.get('size') in DIMENSIONS and values.get('design_width') and values.get('design_height'):
        if tuple(sorted([values['design_width'],values['design_height']])) != tuple(sorted(DIMENSIONS[values['size']])):
            issue('design_width','Design dimensions','Confirm the design matches the ordered flyer size.')
    if adapter=='mortgage':
        for earlier, later, label in [
            ('registration_date','default_date','Default date'),('default_date','as_of','Calculation date'),
            ('registration_date','transfer_date','Transfer date'),('transfer_date','as_of','Calculation date')]:
            if values.get(earlier) and values.get(later) and values[earlier] > values[later]:
                issue(later,label,f'Check chronology. {label} precedes a prior recorded event.')
        if values.get('transferred_lender') and not values.get('transfer_date'):
            issue('transfer_date','Transfer date','Provide the transfer-of-charge date.')
        if values.get('payment_history') and 'no payments during calculation period' not in values['payment_history'].lower():
            issue('payment_history','Payment history','This illustrative calculator requires a ledger confirming no payments during the calculation period.')
    return results

def make_output(workflow, values):
    values={spec['key']:values[spec['key']] for spec in workflow['fields'] if spec['key'] in values}
    title=workflow['title']
    lines=[f"{s['label']}: {values[s['key']]}" for s in workflow['fields'] if s['key'] in values]
    sections={}
    calculation={}
    adapter=workflow.get('adapter')
    if adapter=='transport':
        title="Transport order"
        sections['TMS preview']='Synthetic local TMS field preview based on the challenge brief.'
    elif adapter=='print':
        title="Flyer order and proposed pricing"
        base=Decimal(workflow['prices'][values['size']])
        sides=Decimal(workflow['prices']['double_sided']) if values['sides']=='Double-sided' else Decimal(0)
        discount=Decimal(workflow['prices']['black_and_white_discount']) if values['colour']=='Black and white' else Decimal(0)
        unit=base+sides-discount
        calculation=dict(currency="CAD",quantity=values['quantity'],base_per_flyer=money(base),
                         sides_surcharge=money(sides),colour_discount=money(discount),unit_price=money(unit),
                         total=money(unit*Decimal(str(values['quantity']))))
        sections['Synthetic pricing']=printing_reference(workflow)
        sections['Design review']=f"{values['design']} · {values['design_width']} × {values['design_height']} mm · {values['resolution']} DPI. Owner verifies the supplied design and proposed invoice."
    elif adapter=='mortgage':
        title="Mortgage enforcement case"
        days=(date.fromisoformat(values['as_of'])-date.fromisoformat(values['default_date'])).days
        principal=Decimal(values['principal'])
        rate=Decimal(str(values['rate']))
        fees=Decimal(values['fees'])
        interest=(principal*rate/Decimal(100)*days/Decimal(365)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
        calculation=dict(method=values['method'],currency='CAD',days=days,principal=money(principal),
                         rate_pct=str(rate),interest=money(interest),fees=money(fees),total=money(principal+interest+fees))
        sections['Calculation']=f"CAD {money(principal)} × {rate}% × {days}/365 = CAD {money(interest)} interest. Principal + rounded interest + CAD {money(fees)} verified fees = CAD {calculation['total']}."
        parties=values | {'lender':values.get('transferred_lender',values['lender']),'total':calculation['total']}
        for label,filename in [('Demand Letter','demand.txt'),('Statement of Claim','claim.txt')]:
            sections[label]=(ROOT/'templates'/filename).read_text().format_map(parties).strip()
    elif adapter=='accommodation':
        title="Workplace accommodation plan"
        needs=values['needs']
        sections={
            'Interview': 'Ask the candidate to confirm preferred interview format and provide instructions in an accessible format before the interview.',
            'Day-one setup':f"Confirm and test requested adjustments with the candidate and IT. Candidate-stated needs: {needs}",
            'Training':'Provide accessible digital materials in advance and confirm with the candidate that training tools and job systems work with their preferred settings.',
            'Ongoing support':'Assign a staff contact. Check in after the first week and adjust the setup based on the candidate’s feedback.',
            'Costs':'Pending staff verification. Confirm existing licences, equipment and any procurement costs.',
            'Employer questions':f"Recorded provisions: {values['provisions']}. Who owns setup, which tools are available and when can the candidate test them?",
        }
        if 'magnification' in needs.lower():
            sections['Day-one setup']+=' Verify magnification and keyboard navigation in the support portal on the workstation that will be used.'
            sections['Training']+=' Offer large-print instructions or accessible digital equivalents and practise a support task together.'
        lines=[f"Candidate: {values['candidate']}",f"Role: {values['role']}"]
    if workflow.get('template'):
        import re
        sections['Configured output']=re.sub(r'\{([a-z][a-z0-9_]*)\}',lambda match:str(values.get(match[1],'')),workflow['template'])
    return dict(title=title,summary='\n'.join(lines),sections=sections,calculation=calculation,values=values,format=workflow['output'])
