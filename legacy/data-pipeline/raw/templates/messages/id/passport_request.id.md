# passport_request.id

## template_id
msg_passport_request_id

## purpose
passport_request

## korean_original
비자 업무 확인을 위해 여권 사본이 필요합니다. {due_date}까지 사진으로 보내주세요. 수집한 서류는 체류·고용 관련 행정 업무 확인 목적으로만 사용됩니다. 문의사항은 {contact_person}에게 확인해주세요.

## indonesian_draft
Harap mengirimkan foto salinan paspor sebelum tanggal {due_date}. Dokumen ini hanya akan digunakan untuk memeriksa administrasi terkait izin tinggal dan pekerjaan. Jika ada pertanyaan, silakan hubungi {contact_person}.

## required_fields
- worker_name
- due_date
- privacy_purpose
- contact_person

## approval_required
true

## source_id
templates_messages

## review_status
needs_human_review

## notes
MVP 인도네시아어 서비스용. 개인정보/서류 요청이므로 담당자 승인 전 발송 금지.
