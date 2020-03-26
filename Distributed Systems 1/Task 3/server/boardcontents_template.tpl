<!-- this place will show the actual contents of the blackboard.
It will be reloaded automatically from the server -->
<div id="boardcontents_placeholder">
	<!-- The title comes here -->
	<div id="boardtitle_placeholder" class="boardtitle">{{board_title}}</div>
    <input type="text" name="id_header" value="Seq Num" size=9 readonly>
    <input type="text" name="id_header" value="Sender_ID" size=9 readonly>
    <input type="text" name="entry_header" value="Entry" size="35" readonly>
    % for row in board_dict:
		<form class="entryform" target="noreload-form-target" method="post" action="/board/{{row['entry'] if 'entry' in row else 0}}/">
			<input type="text" name="id" value="{{row['id'] if 'id' in row else "ID_NONE" }}" size=9 readonly disabled> <!-- disabled field won’t be sent -->
			<input type="text" name="orig_node_id" value="{{row['sender_id'] if 'sender_id' in row else "ID_NONE" }}" size=9>
			<input type="text" name="entry" value="{{row['entry'] if 'entry' in row else "ENTRY_NONE"}}" size="35">
			<button type="submit" name="modify" value="0" method="post" formaction="/propagate/0/{{row['id']}}">Modify</button>
			<button type="submit" name="delete" value="1" method="post" formaction="/propagate/1/{{row['id']}}">X</button>
		</form>
    %end
</div>
