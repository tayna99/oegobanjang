# photo_request.vi

## template_id
msg_photo_request_vi

## purpose
photo_request

## korean_original
행정 업무 확인을 위해 증명사진 파일이 필요합니다. {due_date}까지 사진 파일을 보내주세요. 사진은 체류·고용 관련 행정 업무 확인 목적으로만 사용됩니다. 문의사항은 {contact_person}에게 확인해주세요.

## vietnamese_draft
Vui lòng gửi tệp ảnh thẻ trước ngày {due_date} để kiểm tra thủ tục hành chính. Ảnh này chỉ được sử dụng cho các thủ tục hành chính liên quan đến cư trú và việc làm. Nếu có thắc mắc, vui lòng liên hệ {contact_person}.

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
MVP 베트남어 서비스용. 증명사진은 개인정보성 자료이므로 담당자 승인 전 발송 금지.
