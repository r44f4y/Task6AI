import re
from datetime import date, datetime
from decimal import Decimal,InvalidOperation

def normalize(field, raw):
    """Return a canonical value and an optional validation issue."""
    if raw is None or (isinstance(raw,str) and not raw.strip()):
        return None,None
    kind = field['type']
    value = str(raw).strip()
    value = str(field.get('aliases',{}).get(value.casefold(),value))
    if kind in ('number','currency'):
        try:
            numeric=value.removeprefix('CAD ').removeprefix('$').strip()
            if not re.fullmatch(r'[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?',numeric):
                raise InvalidOperation
            number = Decimal(numeric.replace(',',''))
            if not number.is_finite() or abs(number)>Decimal('1e15'):
                raise InvalidOperation
            if field.get('minimum') is not None and number < Decimal(str(field['minimum'])):
                return None, f"Enter at least {field['minimum']}."
            if field.get('maximum') is not None and number > Decimal(str(field['maximum'])):
                return None, f"Enter at most {field['maximum']}."
            if field.get('integer') and number != number.to_integral_value():
                return None, "Enter a whole number."
            if kind=='currency':
                return format(number.quantize(Decimal('0.01')),'f'),None
            return int(number) if number == number.to_integral_value() else float(number),None
        except (InvalidOperation, ValueError):
            return None,"Enter a valid number."
    if kind == 'boolean':
        if value.lower() in ('true','yes','required'):
            return True,None
        if value.lower() in ('false','no','not required'):
            return False,None
        return None,"Confirm yes or no."
    if kind == 'date':
        try:
            return date.fromisoformat(value).isoformat(),None
        except ValueError:
            for pattern in ('%B %d, %Y','%b %d, %Y','%d %B %Y','%d %b %Y'):
                try:
                    return datetime.strptime(value,pattern).date().isoformat(),None
                except ValueError:
                    pass
            if re.fullmatch(r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}',value) or re.search(
                r'\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',value,re.I
            ):
                return None,"Ambiguous date. Confirm the calendar date (YYYY-MM-DD)."
            return None,"Enter a valid date (YYYY-MM-DD)."
    if kind == 'time':
        cleaned = re.sub(r'\.', '', value.lower()).strip()
        cleaned = cleaned.replace('in the morning','am').replace('in the afternoon','pm').replace('in the evening','pm')
        match = re.fullmatch(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',cleaned)
        if match:
            hour, minute, period = match.groups()
            hh, mm = int(hour), int(minute or 0)
            if mm > 59 or hh > 23 or (period and not 1 <= hh <= 12):
                return None, "Enter a valid time."
            if period:
                hh = hh % 12 + (12 if period == 'pm' else 0)
            elif not minute or (1<=hh<=12 and len(hour)==1):
                return None,"Ambiguous time. Confirm AM or PM."
            return f'{hh:02d}:{mm:02d}',None
        return None,"Enter a clear time in 24-hour format or with AM/PM."
    if kind == 'email' and not re.fullmatch(r'[^@\s<>]+@[^@\s<>]+\.[a-zA-Z]{2,}',value):
        return None,"Enter a valid email address."
    if kind == 'phone':
        digits = re.sub(r'[^0-9]','',value)
        if not re.fullmatch(r'\+?[\d() .-]+',value) or len(digits) not in (10,11):
            return None,"Enter a phone number with area code."
    if kind == 'address' and not re.match(r'^\d+[A-Za-z]?\s+\S+.+,\s*\S+',value):
        return None,"Confirm the street number, street name and municipality."
    if kind == 'select':
        option = next((item for item in field['options'] if item.lower()==value.lower()),None)
        if option is None:
            return None, "Select " + " or ".join(field['options']) + "."
        return option,None
    return value,None

def required_field(spec, fields):
    condition = spec.get('when')
    return spec['required'] or bool(condition and fields.get(condition['field'],{}).get('value') == condition['equals'])

def evaluate(workflow, fields):
    issues=[]
    required = 0
    resolved = 0
    for spec in workflow['fields']:
        key = spec['key']
        record = fields.get(key,{})
        status = record.get('status','MISSING')
        needed = required_field(spec, fields)
        if needed:
            required += 1
            if status in ('EXTRACTED','HUMAN_VERIFIED'):
                resolved += 1
            elif status=='MISSING':
                issues.append(dict(key=key,kind=status,detail=f"Provide {spec['label'].lower()}.",label=spec['label']))
        if status in ('INVALID','AMBIGUOUS','CONFLICTING'):
            issues.append(dict(key=key,kind=status,detail=record['issue'],label=spec['label']))
    return issues,required,resolved
