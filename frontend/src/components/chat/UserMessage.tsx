import type { UserChatMessage } from "@/lib/types";

interface UserMessageProps {
  message: UserChatMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-[15px] leading-6 text-primary-foreground shadow-sm">
        {message.content}
      </div>
    </div>
  );
}
