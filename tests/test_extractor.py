import unittest

from extractor import extract_prescription_fields


class PrescriptionExtractionTests(unittest.TestCase):
    def test_extracts_fields_from_prescription_sentence(self):
        text = "Paracetamol 500 mg 1 tab twice daily for 5 days"
        fields = extract_prescription_fields(text)

        self.assertEqual(fields['medicine'], 'Paracetamol')
        self.assertEqual(fields['strength'], '500 MG')
        self.assertEqual(fields['dosage'], '1 Tab')
        self.assertEqual(fields['frequency'], 'TWICE DAILY')
        self.assertEqual(fields['duration'], '5 Days')

    def test_normalizes_common_abbreviations(self):
        text = "Amoxicillin 250 mg 2 capsules BD for 7 days"
        fields = extract_prescription_fields(text)

        self.assertEqual(fields['medicine'], 'Amoxicillin')
        self.assertEqual(fields['strength'], '250 MG')
        self.assertEqual(fields['dosage'], '2 Capsules')
        self.assertEqual(fields['frequency'], 'TWICE DAILY')
        self.assertEqual(fields['duration'], '7 Days')

    def test_stops_medicine_extraction_before_field_header(self):
        text = "Medicine: Paracetamol Dosage: 1 tablet Frequency: 2x daily Duration: 5 days"
        fields = extract_prescription_fields(text)

        self.assertEqual(fields['medicine'], 'Paracetamol')
        self.assertEqual(fields['dosage'], '1 Tablet')
        self.assertEqual(fields['frequency'], 'TWICE DAILY')
        self.assertEqual(fields['duration'], '5 Days')

    def test_normalizes_times_per_day_frequencies(self):
        # Test x daily forms
        text_2x = "Paracetamol 500 mg 2x daily for 3 days"
        self.assertEqual(extract_prescription_fields(text_2x)['frequency'], 'TWICE DAILY')

        text_3x = "Amoxicillin 250 mg 3x daily for 7 days"
        self.assertEqual(extract_prescription_fields(text_3x)['frequency'], 'THREE TIMES A DAY')

        text_once = "Cetirizine 10 mg once daily for 10 days"
        self.assertEqual(extract_prescription_fields(text_once)['frequency'], 'ONCE DAILY')

    def test_filters_out_person_and_clinic_names(self):
        # Patient's name should not be extracted as medicine
        text_person = "Patient Name: Priya Shakthi Age: 25 Medicine: Paracetamol 500 mg"
        self.assertEqual(extract_prescription_fields(text_person)['medicine'], 'Paracetamol')

        # Clinic header should not be extracted as medicine
        text_clinic = "Health Plus City Care Clinic Name: Mohan Raj Medicine: Metformin 500 mg"
        self.assertEqual(extract_prescription_fields(text_clinic)['medicine'], 'Metformin')

    def test_rejects_single_letter_medicine_and_metadata_dosages(self):
        # OCR noise resulting in single letter medicine name should be rejected
        text_noise = "SRI VARI CLINIC Dr. F No. 15/2 East Street Medicine: Paracetamol"
        self.assertEqual(extract_prescription_fields(text_noise)['medicine'], 'Paracetamol')

        # Medicine starting with a digit/number should be rejected
        text_digit_noise = "3t 3in/172 Medicine: Metformin"
        self.assertEqual(extract_prescription_fields(text_digit_noise)['medicine'], 'Metformin')

        # Address strings should not be matched as medicine names
        text_addr_med = "CITY CARE CLINIC No. 32, Ist Main Road, Ashok Nagar; Chennai Medicine: Metformin"
        self.assertEqual(extract_prescription_fields(text_addr_med)['medicine'], 'Metformin')

        # Address numbers, phone numbers, and postcodes should not match as bare dosage
        text_addr = "Clinic Address: No. 15/2 Main Road PIN 600041 Reg No. 59321 Tel 24567345 Date 03/08/2026. Medicine: Metformin Dosage: 2"
        fields = extract_prescription_fields(text_addr)
        self.assertEqual(fields['dosage'], '2')


if __name__ == '__main__':
    unittest.main()
