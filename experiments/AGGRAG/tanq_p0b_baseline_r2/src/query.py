"""Traditional parameterized EAV query + deterministic wide-table pivot."""
import sqlite3,collections
from contracts import norm,text,number,validate_plan,columns_for,render_table

def compile_plan(plan):
    valid=validate_plan(plan)
    if valid['status']!='PLAN_VALID_STRUCTURAL':return valid
    cat={norm(p['name']):p for p in plan['predicates']};params=[norm(plan['entity_type'])]
    def compile_node(node):
        if 'conditions' in node:
            if not node['conditions']:return '1=1' # only empty AND is allowed by validator
            op=' AND ' if node['op']=='and' else ' OR '
            return '('+op.join(compile_node(c) for c in node['conditions'])+')'
        key=norm(node['predicate']);p=cat[key];params.append(key)
        column='object_key' if p['kind']=='text' else 'numeric_value'
        operators={'eq':'=','lt':'<','le':'<=','gt':'>','ge':'>='}
        params.append(norm(node['value']) if p['kind']=='text' else float(node['value']))
        return ('EXISTS (SELECT 1 FROM facts AS c WHERE c.subject_key=f.subject_key '
                'AND c.entity_type_key=f.entity_type_key AND c.predicate_key=? AND c.'+column+operators[node['operator']]+'?)')
    sql='SELECT DISTINCT f.subject_key FROM facts AS f WHERE f.entity_type_key=? AND '+compile_node(plan['filter'])+' ORDER BY f.subject_key'
    return {'status':'PLAN_COMPILED','sql':sql,'parameters':params,'all_identifiers_generated_by_program':True}

def execute_plan(facts,plan):
    compiled=compile_plan(plan)
    if compiled['status']!='PLAN_COMPILED':return {'status':'PLAN_INVALID','plan_validation':compiled,'join_completed':False}
    cat={norm(p['name']):p for p in plan['predicates']}
    if not isinstance(facts,list):return {'status':'JOIN_INVALID','reason':'FACT_INPUT_MUST_BE_LIST','join_completed':False}
    for f in facts:
        if not isinstance(f,dict) or not {'subject','entity_type','predicate','value','evidence_id','quote','raw_index'}<=set(f):return {'status':'JOIN_INVALID','reason':'VALIDATED_FACT_INPUT_REQUIRED','raw':facts,'join_completed':False}
        if not all(text(f[k]) for k in ('subject','entity_type','predicate','evidence_id')) or not isinstance(f['raw_index'],int) or isinstance(f['raw_index'],bool):return {'status':'JOIN_INVALID','reason':'INVALID_FACT_FIELD_TYPE','raw':facts,'join_completed':False}
        p=cat.get(norm(f['predicate']))
        if p is None or norm(f['entity_type'])!=norm(plan['entity_type']) or (p['kind']=='number' and not number(f['value'])) or (p['kind']=='text' and not text(f['value'])):return {'status':'JOIN_INVALID','reason':'FACT_DOES_NOT_SATISFY_PLAN_TYPES','raw':facts,'join_completed':False}
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE facts(subject_key TEXT,subject TEXT,entity_type_key TEXT,predicate_key TEXT,object TEXT,object_key TEXT,numeric_value REAL,evidence_id TEXT,raw_index INTEGER)')
    for f in facts:
        k=norm(f['predicate']);v=f['value'];p=cat[k]
        db.execute('INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?)',(norm(f['subject']),f['subject'],norm(f['entity_type']),k,str(v),norm(str(v)),float(v) if p['kind']=='number' else None,f['evidence_id'],f['raw_index']))
    db.commit()
    def authorize(action,a,b,dbname,trigger):
        if action==sqlite3.SQLITE_SELECT:return sqlite3.SQLITE_OK
        if action==sqlite3.SQLITE_READ:return sqlite3.SQLITE_OK if a=='facts' else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_DENY
    db.set_authorizer(authorize);ticks=[0]
    def progress():ticks[0]+=1;return ticks[0]>1000
    db.set_progress_handler(progress,1000)
    try:
        selected=[r[0] for r in db.execute(compiled['sql'],compiled['parameters']).fetchmany(10001)]
        if len(selected)>10000:return {'status':'JOIN_INVALID','reason':'ROW_LIMIT','join_completed':False}
        groups=collections.defaultdict(list)
        for f in facts:groups[norm(f['subject'])].append(f)
        conflicts=[];rows=[];lineage=[]
        for key in selected:
            entries=groups[key];byattr=collections.defaultdict(list)
            for f in entries:byattr[norm(f['predicate'])].append(f)
            bad=[k for k,vs in byattr.items() if cat[k]['cardinality']=='one' and len({norm(str(f['value'])) for f in vs})>1]
            if bad:conflicts.append({'entity_key':key,'predicates':bad,'reason':'SINGLE_VALUE_CONFLICT','facts':entries});continue
            row=[entries[0]['subject']];cells=[]
            for o in plan['outputs']:
                values={}
                for f in byattr[norm(o['predicate'])]:values.setdefault(norm(str(f['value'])),str(f['value']))
                row.append(', '.join(values[k] for k in sorted(values)) if values else None)
                cells.append({'predicate':o['predicate'],'facts':byattr[norm(o['predicate'])]})
            rows.append(row);lineage.append({'entity_key':key,'cells':cells})
        table={'columns':columns_for(plan),'rows':rows};rendered=render_table(table,plan)
        if rendered['status']!='RENDERED':return {'status':'JOIN_INVALID','reason':'TABLE_CONTRACT','join_completed':True,'validation':rendered,'compiled':compiled,'raw_table':table}
        return {'status':'JOIN_PARTIAL' if conflicts else 'JOIN_COMPLETED','join_completed':True,'table':table,'prediction':rendered['text'],'compiled':compiled,'lineage':lineage,'conflicts':conflicts,'not_selected_entity_keys':sorted(set(groups)-set(selected)),'selection_scope':'EXTRACTED_FACTS_ONLY; not world completeness','semantic_support':'UNVERIFIED'}
    except sqlite3.Error as e:return {'status':'JOIN_INVALID','reason':str(e),'compiled':compiled,'join_completed':False}
    finally:db.close()
