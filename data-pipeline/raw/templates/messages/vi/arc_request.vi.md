# arc_request.vi

## template_id
msg_arc_request_vi

## purpose
arc_request

## korean_original
체류·고용 관련 행정 업무 확인을 위해 외국인등록증 사본이 필요합니다. {due_date}까지 앞면과 뒷면 사진을 보내주세요. 수집한 서류는 행정 업무 확인 목적으로만 사용됩니다. 문의사항은 {contact_person}에게 확인해주세요.

## vietnamese_draft
Để kiểm tra thủ tục hành chính liên quan đến cư trú và việc làm, vui lòng gửi ảnh chụp mặt trước và mặt sau của thẻ đăng ký người nước ngoài trước ngày {due_date}. Tài liệu này chỉ được sử dụng cho mục đích kiểm tra hành chính. Nếu có thắc mắc, vui lòng liên hệ {contact_person}.

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
MVP 베트남어 서비스용. 외국인등록증 요청은 민감한 서류 요청이므로 담당자 승인 전 발송 금지.
