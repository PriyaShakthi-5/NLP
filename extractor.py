import re
import spacy
from ocr import run_ocr

try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    nlp = None

FIELD_LABELS = {
    'patient_name': ['patient name', 'patient', 'pt name', 'pt. name', 'name'],
    'medicine': ['medicine', 'medication', 'drug', 'tablet', 'capsule', 'syrup'],
    'dosage': ['dosage', 'dose', 'quantity', 'qty', 'take'],
    'strength': ['strength', 'concentration', 'dose'],
    'frequency': ['frequency', 'freq', 'schedule', 'daily', 'bd', 'tid', 'qid', 'od', 'prn'],
    'duration': ['duration', 'for', 'days', 'weeks', 'months'],
}

GENERIC_WORDS = {
    'medicine', 'medication', 'drug', 'tablet', 'tablets', 'capsule', 'capsules', 'syrup',
    'take', 'takes', 'prescribe', 'prescription', 'use', 'administer', 'patient', 'doctor'
}

INVALID_MEDICINE_TOKENS = {
    'for', 'bd', 'tid', 'qid', 'od', 'prn', 'day', 'days', 'week', 'weeks', 'month', 'months',
    'mg', 'ml', 'mcg', 'g', 'tab', 'tabs', 'tablet', 'tablets', 'capsule', 'capsules'
}

FREQUENCY_MAP = {
    'bd': 'TWICE DAILY',
    'tid': 'THREE TIMES A DAY',
    'qid': 'FOUR TIMES A DAY',
    'od': 'ONCE DAILY',
    'prn': 'AS NEEDED',
    'once daily': 'ONCE DAILY',
    'twice daily': 'TWICE DAILY',
    'three times a day': 'THREE TIMES A DAY',
    'four times a day': 'FOUR TIMES A DAY',
    'every 12 hours': 'TWICE DAILY',
    'every 8 hours': 'THREE TIMES A DAY',
    'every 6 hours': 'FOUR TIMES A DAY',
}

UNIT_MAP = {
    'tab': 'Tab',
    'tabs': 'Tabs',
    'tablet': 'Tablet',
    'tablets': 'Tablets',
    'capsule': 'Capsule',
    'capsules': 'Capsules',
    'ml': 'ML',
    'mg': 'MG',
    'mcg': 'MCG',
    'g': 'G',
}


def _clean_text(value):
    return re.sub(r'\s+', ' ', value).strip()


def _contains_label(sentence, labels):
    lowered = sentence.lower()
    return any(label in lowered for label in labels)


def _is_valid_bare_dosage(num_str, context_before, context_after):
    context_lowered = context_before.lower().strip()
    
    reject_patterns = [
        r'\bno\.?\W*$', r'\breg\.?\W*$', r'\bph\.?\W*$', r'\btel\.?\W*$', 
        r'\bphone\W*$', r'\bdate\W*$', r'\bage\W*$', r'\bsex\W*$', r'\bpin\s*code\W*$'
    ]
    if any(re.search(pat, context_lowered) for pat in reject_patterns):
        return False
        
    if re.match(r'^\s*[\-/]\s*\d{2,4}', context_after):
        return False
        
    try:
        if '/' in num_str:
            parts = num_str.split('/')
            val = float(parts[0]) / float(parts[1])
        elif '-' in num_str:
            parts = num_str.split('-')
            val = float(parts[-1])
        else:
            val = float(num_str)
        return val <= 20.0
    except (ValueError, ZeroDivisionError):
        return False


def _is_valid_medicine(candidate, extra_blocked_tokens=None):
    """Filters out clinic names, patient names, generic words, and headers from medicine names."""
    cleaned = candidate.strip().lower()
    if not cleaned or len(cleaned) < 3 or cleaned in GENERIC_WORDS:
        return False
        
    first_char = re.search(r'[a-z0-9]', cleaned)
    if first_char and not first_char.group(0).isalpha():
        return False
    
    tokens = set(cleaned.replace('-', ' ').split())
    if tokens & INVALID_MEDICINE_TOKENS:
        return False

    invalid_keywords = {
        'clinic', 'hospital', 'medical', 'note', 'patient', 'doctor', 'dr', 
        'name', 'date', 'age', 'sex', 'gender', 'mbbs', 'md', 'dch', 'dnb', 'reg',
        'care', 'health', 'university', 'college', 'science', 'education',
        'contact', 'phone', 'email', 'experience', 'internship', 'project',
        'skills', 'summary', 'achievements', 'hsc', 'sslc',
        'female', 'male', 'transgender', 'other', 'years', 'yrs', 'yo', 'year',
        'weight', 'height', 'bp', 'blood', 'pressure', 'temp', 'temperature', 'pulse', 'heart', 'rate',
        'signature', 'sign', 'history', 'symptoms', 'diagnosis',
        'road', 'street', 'avenue', 'lane', 'nagar', 'cross', 'main', 'floor', 
        'building', 'block', 'sector', 'phase', 'city', 'town', 'state', 'country', 
        'seattle', 'atlanta', 'chennai', 'bangalore', 'mumbai', 'delhi', 'india', 'district', 'zone', 
        'west', 'east', 'north', 'south', 'no', 'number', 'address', 'near',
        'opp', 'opposite', 'behind',
        'frequency', 'dosage', 'duration', 'strength', 'rx', 'prescription',
        'medicine', 'medication', 'quantity', 'qty', 'tablet', 'tablets',
        'capsule', 'capsules', 'tablet(s)', 'capsule(s)'
    }
    if extra_blocked_tokens:
        invalid_keywords.update(extra_blocked_tokens)

    if tokens & invalid_keywords:
        return False

    if nlp:
        cand_doc = nlp(candidate)
        for ent in cand_doc.ents:
            if ent.label_ == 'PERSON':
                return False

    return bool(re.search(r'[A-Za-z]', cleaned))


def _normalize_frequency(value):
    normalized = _clean_text(value).lower()
    if normalized in FREQUENCY_MAP:
        return FREQUENCY_MAP[normalized]

    match_day = re.search(r'\b(\d+)\s*x\s*(?:a\s*)?(?:day|daily)\b', normalized)
    if match_day:
        amount = int(match_day.group(1))
        if amount == 1:
            return 'ONCE DAILY'
        if amount == 2:
            return 'TWICE DAILY'
        if amount == 3:
            return 'THREE TIMES A DAY'
        if amount >= 4:
            return 'FOUR TIMES A DAY'

    return _clean_text(value).upper()


def _normalize_duration(value):
    match = re.search(r'(\d+)\s*(day|days|week|weeks|month|months)', value, re.IGNORECASE)
    if match:
        quantity = match.group(1)
        unit = match.group(2).lower()
        if unit in {'day', 'week', 'month'}:
            unit = f"{unit}s"
        return f"{quantity} {unit.capitalize()}"
    return _clean_text(value).title()


def _normalize_unit(value, pattern, format_type):
    match = re.search(pattern, value, re.IGNORECASE)
    if match:
        qty = match.group(1)
        unit = match.group(2).lower()
        mapped_unit = UNIT_MAP.get(unit, unit)
        return f"{qty} {mapped_unit}"
    if format_type == 'title':
        return _clean_text(value).title()
    return _clean_text(value).upper()


def _normalize_dosage(value):
    return _normalize_unit(value, r'(\d+)\s*(capsules?|tablets?|tabs?)', 'title')


def _normalize_strength(value):
    return _normalize_unit(value, r'(\d+)\s*(mg|ml|mcg|g)', 'upper')


def _is_address_or_metadata_sentence(sentence):
    lowered = sentence.lower()
    
    if any(k in lowered for k in ['mg', 'ml', 'mcg', 'tablet', 'capsule', 'tabs', 'drug', 'medicine', 'medication']):
        return False
        
    address_keywords = [
        'road', 'street', 'avenue', 'lane', 'nagar', 'cross', 'main', 'floor', 
        'building', 'block', 'sector', 'phase', 'city', 'town', 'state', 'country',
        'hospital', 'clinic', 'ph:', 'phone', 'tel:', 'email', 'date:', 'patient', 
        'doctor', 'dr.', 'signature', 'sign:', 'age:', 'sex:', 'gender:', 'years', 'yrs'
    ]
    if any(k in lowered for k in address_keywords):
        return True
        
    if re.search(r'\b\d{5,6}\b', lowered):
        return True
        
    return False


def _extract_patient_name(text):
    """Extracts patient name from text matching 'Patient Name: ...' or 'Patient: ...' or 'Name: ...'."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    for i, line in enumerate(lines):
        match = re.search(r'\b(?:patient\s*(?:name)?|pt\.?\s*name|patient\'s\s*name)\s*[:|-]?\s*([A-Za-z\s.]+)', line, re.IGNORECASE)
        if match:
            cand = _clean_text(match.group(1))
            if cand and len(cand.split()) <= 4 and not any(u in cand.lower() for u in ['mg', 'ml', 'tablet', 'capsule', 'tabs', '500', '850', '10']):
                return cand.title()
                
        if re.search(r'^\s*(?:patient\s*(?:name)?|pt\.?\s*name)\s*[:|-]?\s*$', line, re.IGNORECASE):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s.]{2,35}$', next_line) and not _is_address_or_metadata_sentence(next_line):
                    return next_line.title()

    for line in lines:
        match = re.search(r'^\s*name\s*[:|-]\s*([A-Za-z\s.]+)', line, re.IGNORECASE)
        if match:
            cand = _clean_text(match.group(1))
            if cand and len(cand.split()) <= 4 and not any(u in cand.lower() for u in ['mg', 'ml', 'tablet', 'capsule', '500', '850', '10', 'para']):
                return cand.title()
                
    return ''


def _extract_medicine(sentence, sent_doc, blocked_tokens=None):
    """Extracts medicine name while strictly avoiding patient names."""
    if _is_address_or_metadata_sentence(sentence):
        return ''
        
    patterns = [
        (r'\b(?:medicine|medication|drug|tablet|tablets|capsule|capsules|syrup)\b\s*(?:is|:|-)?\s*((?:(?!\b(?:dosage|dose|frequency|duration|strength|patient|is|for|daily)\b)[A-Za-z0-9/\- ])+)', 1),
        (r'(^|\s)([A-Za-z][A-Za-z0-9./-]*(?:\s+[A-Za-z][A-Za-z0-9./-]*){0,3})\b(?:\s+\d+)?\s*(?:mg|ml|mcg|g)\b', 2),
    ]
    for pattern, group_index in patterns:
        match = re.search(pattern, sentence, re.IGNORECASE)
        if match:
            candidate = _clean_text(match.group(group_index))
            if _is_valid_medicine(candidate, blocked_tokens):
                return candidate.title()

    if sent_doc:
        for ent in sent_doc.ents:
            if ent.label_ in {'PRODUCT', 'ORG', 'NORP'}:
                candidate = _clean_text(ent.text)
                if _is_valid_medicine(candidate, blocked_tokens):
                    return candidate.title()

        for chunk in sent_doc.noun_chunks:
            candidate = _clean_text(chunk.text)
            if len(candidate.split()) <= 4 and _is_valid_medicine(candidate, blocked_tokens):
                return candidate.title()

    first_match = re.match(r'^\W*([A-Za-z][A-Za-z0-9./-]*(?:\s+[A-Za-z][A-Za-z0-9./-]*){0,3})\b', sentence)
    if first_match:
        candidate = _clean_text(first_match.group(1))
        tokens = candidate.split()
        if len(tokens) <= 3 and _is_valid_medicine(candidate, blocked_tokens):
            if not any(token.lower() in {'bd', 'tid', 'qid', 'prn', 'for', 'od'} for token in tokens):
                return candidate.title()

    return ''


def _extract_from_context(sentence, field_name, patient_name=''):
    cleaned = _clean_text(sentence)
    sent_doc = nlp(cleaned) if nlp else None

    if field_name == 'patient_name':
        return _extract_patient_name(cleaned)

    if field_name == 'medicine':
        blocked = set(patient_name.lower().split()) if patient_name else set()
        return _extract_medicine(cleaned, sent_doc, blocked)

    if field_name == 'dosage':
        m = re.search(r'(\d+)\s*(capsules?|tablets?|tabs?)', cleaned, re.IGNORECASE)
        if m:
            return _normalize_dosage(m.group(0))
        m = re.search(r'(\d+)\s*(mg|ml|mcg|g)', cleaned, re.IGNORECASE)
        if m:
            return _normalize_strength(m.group(0))
        for match in re.finditer(r'\b([0-9]+(?:\s*[\-/][\s*]?[0-9]+)?)\b', cleaned):
            num_str = match.group(1)
            context_before = cleaned[:match.start()]
            context_after = cleaned[match.end():]
            if _is_valid_bare_dosage(num_str, context_before, context_after):
                return num_str

    if field_name == 'strength':
        m = re.search(r'(\d+)\s*(mg|ml|mcg|g)', cleaned, re.IGNORECASE)
        if m:
            return _normalize_strength(m.group(0))

    if field_name == 'frequency':
        m = re.search(
            r'\b(once\s*daily|twice\s*daily|three\s*times\s*a\s*day|four\s*times\s*a\s*day|every\s*\d+\s*hours|\d+\s*x\s*(?:a\s*)?day|\d+\s*x\s*daily|bd|tid|qid|od|prn)\b',
            cleaned,
            re.IGNORECASE
        )
        if m:
            return _normalize_frequency(m.group(1))

    if field_name == 'duration':
        m = re.search(r'\b(\d+\s*(day|days|week|weeks|month|months))\b', cleaned, re.IGNORECASE)
        if m:
            return _normalize_duration(m.group(1))

    return ''


def _extract_from_text(text, field_name, patient_name=''):
    if not text:
        return ''

    cleaned_text = _clean_text(text)

    if field_name == 'patient_name':
        return _extract_patient_name(text)

    if field_name != 'medicine':
        value = _extract_from_context(cleaned_text, field_name, patient_name)
        if value:
            return value

    sentences = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        doc = nlp(line) if nlp else None
        if doc:
            sentences.extend([sent.text.strip() for sent in doc.sents if sent.text.strip()])
        else:
            sentences.append(line)

    for sentence in sentences:
        if _contains_label(sentence, FIELD_LABELS.get(field_name, [])) or (field_name == 'duration' and 'for' in sentence.lower()):
            value = _extract_from_context(sentence, field_name, patient_name)
            if value:
                return value

    for sentence in sentences:
        value = _extract_from_context(sentence, field_name, patient_name)
        if value:
            return value

    if field_name == 'strength':
        match = re.search(r'\b(\d+\s*(mg|ml|mcg|g))\b', cleaned_text, re.IGNORECASE)
        if match:
            return _normalize_strength(match.group(1))

    if field_name == 'frequency':
        match = re.search(
            r'\b(once\s*daily|twice\s*daily|three\s*times\s*a\s*day|four\s*times\s*a\s*day|every\s*\d+\s*hours|\d+\s*x\s*(?:a\s*)?day|\d+\s*x\s*daily|bd|tid|qid|od|prn)\b',
            cleaned_text,
            re.IGNORECASE
        )
        if match:
            return _normalize_frequency(match.group(1))

    if field_name == 'duration':
        match = re.search(r'\b(\d+\s*(day|days|week|weeks|month|months))\b', cleaned_text, re.IGNORECASE)
        if match:
            return _normalize_duration(match.group(1))

    return ''


def _extract_patient_name(text):
    """Extracts patient name from text matching 'Patient Name: ...' or 'Patient: ...' or 'Name: ...'."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for i, line in enumerate(lines):
        match = re.search(r'\b(?:patient\s*(?:name)?|pt\.?\s*name|patient\'s\s*name|name)\s*[:|-]\s*([A-Za-z\s.]+)', line, re.IGNORECASE)
        if match:
            cand = _clean_text(match.group(1))
            if cand and len(cand.split()) <= 4 and not any(u in cand.lower() for u in ['mg', 'ml', 'tablet', 'capsule', 'tabs', '500', '850', '10', 'amoxicillin', 'cetirizine', 'metformin', 'paracetamol']):
                return cand.title()
                
        if re.search(r'^\s*(?:patient\s*(?:name)?|pt\.?\s*name|name)\s*[:|-]?\s*$', line, re.IGNORECASE):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if re.match(r'^[A-Za-z\s.]{2,35}$', next_line) and not _is_address_or_metadata_sentence(next_line):
                    cand = _clean_text(next_line)
                    if not any(u in cand.lower() for u in ['mg', 'ml', 'tablet', 'capsule', 'tabs', '500', '850', '10', 'date', 'sex', 'age', 'male', 'female', 'amoxicillin', 'cetirizine', 'metformin', 'paracetamol']):
                        return cand.title()

    return ''


def extract_prescription_fields(text):
    result = {
        'patient_name': '',
        'medicine': '',
        'dosage': '',
        'strength': '',
        'frequency': '',
        'duration': ''
    }

    result['patient_name'] = _extract_patient_name(text)

    for key in ['medicine', 'dosage', 'strength', 'frequency', 'duration']:
        result[key] = _extract_from_text(text, key, result['patient_name'])

    return result


def extract_text_from_image(image_path):
    text = run_ocr(image_path)
    fields = extract_prescription_fields(text)
    return {
        'ocr_text': text,
        'fields': fields
    }
