% include('server/board_frontpage_header_template.tpl')
% include('server/boardcontents_template.tpl', board_title=board_title, board_dict=board_dict, elected_leader=elected_leader, max_id=max_id)
% include('server/board_frontpage_footer_template.tpl',members_name_string=members_name_string)