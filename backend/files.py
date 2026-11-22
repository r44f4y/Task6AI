import csv
import io
import json
import re
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from xml.sax.saxutils import escape

import pymupdf
from docx import Document
from openpyxl import Workbook, load_workbook
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

MAX_FILE=5*1024*1024
ALLOWED={'.pdf','.docx','.txt','.csv','.xlsx','.png'}

def safe_name(value):
    return (re.sub(r'[^a-zA-Z0-9_.-]+','_',value).strip('._') or 'file')[:95]

def read_document(filename, data, *, references=False):
    suffix=Path(filename).suffix.lower()
    if suffix not in ALLOWED or (references and suffix=='.png'):
        raise ValueError("Unsupported document type.")
    if not data or len(data)>MAX_FILE:
        raise ValueError("Files must contain data and be 5 MB or smaller.")
    pages=[]
    try:
        if suffix=='.pdf':
            with pymupdf.open(stream=data,filetype='pdf') as pdf:
                if pdf.needs_pass or len(pdf)>60:
                    raise ValueError("PDF is locked or exceeds 60 pages.")
                pages=[{'page':i+1,'text':p.get_text()[:15000]} for i,p in enumerate(pdf)]
        elif suffix in ('.docx','.xlsx'):
            with ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist())>40*1024*1024:
                    raise ValueError("Document exceeds the unpacked size limit.")
            if suffix=='.docx':
                doc=Document(io.BytesIO(data))
                tables=['\n'.join(' | '.join(cell.text for cell in row.cells) for row in table.rows) for table in doc.tables]
                pages=[{'page':None,'text':'\n'.join([p.text for p in doc.paragraphs]+tables)[:15000]}]
            else:
                book=load_workbook(io.BytesIO(data),read_only=True,data_only=True,keep_links=False)
                try:
                    for sheet in book.worksheets[:8]:
                        text='\n'.join(' | '.join(str(v) if v is not None else '' for v in row)
                                       for row in sheet.iter_rows(max_row=250,max_col=30,values_only=True))
                        pages.append({'page':None,'text':(sheet.title+'\n'+text)[:15000]})
                finally:
                    book.close()
        elif suffix=='.png':
            from PIL import Image
            with Image.open(io.BytesIO(data),formats=['PNG']) as image:
                if image.width * image.height > 24_000_000:
                    raise ValueError("PNG exceeds the pixel limit.")
                image.verify()
            with Image.open(io.BytesIO(data),formats=['PNG']) as image:
                dpi=image.info.get('dpi')
                lines=['File format: PNG','Design file: '+safe_name(filename)]
                if dpi and min(dpi)>0:
                    x,y=dpi
                    lines.extend([f'Design width in mm: {round(image.width/x*25.4)}',
                                  f'Design height in mm: {round(image.height/y*25.4)}',
                                  f'Design resolution in DPI: {round(min(dpi))}'])
                pages=[{'page':None,'text':'\n'.join(lines)}]
        else:
            pages=[{'page':None,'text':data.decode('utf-8-sig')[:20000]}]
    except Exception as exc:
        raise ValueError("The document could not be read safely. Check the file format, size or password protection.") from exc
    warning=None if any(p['text'].strip() for p in pages) else "This file has no extractable text. Manual review is required."
    return safe_name(filename), pages, warning

def pdf_bytes(title,text):
    buffer=io.BytesIO()
    styles=getSampleStyleSheet()
    doc=SimpleDocTemplate(buffer,topMargin=45,bottomMargin=45)
    flow=[Paragraph(escape(title),styles['Title']),Spacer(1,10)]
    for line in text.splitlines():
        flow.append(Paragraph(escape(line),styles['BodyText']) if line.strip() else Spacer(1,6))
    doc.build(flow)
    return buffer.getvalue()

def fictional_flyer(width_mm,height_mm,dpi):
    from PIL import Image, ImageDraw, ImageFont
    width,height=(round(mm/25.4*dpi) for mm in (width_mm,height_mm))
    image=Image.new('RGB',(width,height),'#152747')
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,height*.72,width,height),fill='#ebefdb')
    draw.ellipse((width*.52,height*.12,width*.90,height*.12+width*.38),fill='#bdde88')
    draw.rectangle((width*.07,height*.07,width*.42,height*.075),fill='#d5eca7')
    draw.text((width*.07,height*.17),'EXAMPLE ARTS',font=ImageFont.load_default(size=round(width*.055)),fill='#d5eca7')
    headline=ImageFont.load_default(size=round(width*.115))
    draw.text((width*.07,height*.29),'Open studio',font=headline,fill='white',stroke_width=1)
    draw.text((width*.07,height*.40),'day',font=headline,fill='white',stroke_width=1)
    note=ImageFont.load_default(size=round(width*.043))
    draw.text((width*.07,height*.80),'Fictional print specimen',font=note,fill='#152747')
    draw.text((width*.07,height*.87),f'{width_mm} × {height_mm} mm · {dpi} DPI',font=note,fill='#152747')
    buffer=io.BytesIO()
    image.save(buffer,format='PNG',dpi=(dpi,dpi))
    return buffer.getvalue()

def docx_bytes(title,text):
    buffer=io.BytesIO()
    doc=Document()
    doc.add_heading(title,0)
    for line in text.splitlines():
        doc.add_paragraph(line)
    doc.save(buffer)
    return buffer.getvalue()

def sheet_value(value):
    if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@')):
        return "'"+value
    return value

def json_bytes(value):
    return json.dumps(value,ensure_ascii=False,indent=2).encode()

def output_files(workflow,output,request,attachments):
    values=output['values']
    status="Lawyer-reviewed illustrative drafts" if workflow.get('adapter')=='mortgage' else "Approved local record"
    sections={**output['sections']}
    if output.get('staff_edit'):
        sections={'Staff-reviewed plan':output['staff_edit']}
    summary='\n\n'.join([status,output['summary']]+[f'{k}\n{v}' for k,v in sections.items()])
    files={'record.json':json_bytes(output),'evidence.json':json_bytes(request['fields']),
           'conversation.json':json_bytes(request['messages']),'audit-trail.json':json_bytes(request['audit']),
           'review-history.json':json_bytes(request['approvals'])}
    fmt=workflow['output']
    if fmt in ('csv','xlsx') or workflow.get('adapter')=='transport':
        rows=[list(values),[sheet_value(v) for v in values.values()]]
        if fmt=='xlsx':
            wb=Workbook()
            sheet=wb.active
            sheet.title="Printing order"
            for row in rows: sheet.append(row)
            if output['calculation']:
                sheet=wb.create_sheet("Proposed pricing")
                sheet.append(["Synthetic demonstrator pricing","CAD"])
                for key,value in output['calculation'].items(): sheet.append([key,value])
            stream=io.BytesIO()
            wb.save(stream)
            files['order.xlsx']=stream.getvalue()
        else:
            stream=io.StringIO()
            csv.writer(stream).writerows(rows)
            files['order.csv']=stream.getvalue().encode('utf-8')
    if fmt in ('pdf','zip') or workflow.get('adapter')=='transport':
        files['summary.pdf']=pdf_bytes(output['title'],summary)
    if fmt=='docx':
        files['reviewed-record.docx']=docx_bytes(output['title'],summary)
    if workflow.get('adapter')=='mortgage':
        files['demand-letter-DRAFT.docx']=docx_bytes('Demand Letter',sections['Demand Letter'])
        files['statement-of-claim-DRAFT.docx']=docx_bytes('Statement of Claim',sections['Statement of Claim'])
        files['calculation.json']=json_bytes(output['calculation'])
    for index,attachment in enumerate(attachments,1):
        files[f'sources/{index:02d}-{safe_name(attachment.filename)}']=attachment.content
    return files

def zip_bytes(files):
    stream=io.BytesIO()
    with ZipFile(stream,'w',compression=ZIP_DEFLATED) as archive:
        for name,data in files.items(): archive.writestr(name,data)
    return stream.getvalue()
