# passport_request.vi

## template_id
msg_passport_request_vi

## purpose
passport_request

## korean_original
비자 업무 확인을 위해 여권 사본이 필요합니다. {due_date}까지 사진으로 보내주세요. 수집한 서류는 체류·고용 관련 행정 업무 확인 목적으로만 사용됩니다. 문의사항은 {contact_person}에게 확인해주세요.

## vietnamese_draft
Vui lòng gửi ảnh chụp bản sao hộ chiếu trước ngày {due_date}. Tài liệu này chỉ được sử dụng để kiểm tra các thủ tục hành chính liên quan đến cư trú và việc làm. Nếu có thắc mắc, vui lòng liên hệ {contact_person}.

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
MVP 베트남어 서비스용. 개인정보/서류 요청이므로 담당자 승인 전 발송 금지.
