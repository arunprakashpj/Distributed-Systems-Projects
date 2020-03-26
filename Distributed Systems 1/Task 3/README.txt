Video Timestamps
00:00 - 04:05 --> eventual consistency. Boards looks the same. Basic delete/modify works fine
04:05 - 09:16 --> Pending modify. Received the packet to modify the entry earlier then packet that create an entry
09:16 - 14:00 --> Two concurrent delete. We assume that user accidentally clicked delete item twice. So check the time skew, if small, don't add the delete to action_queue
14:00 - 15:34 --> Pros/Cons + solution cost.