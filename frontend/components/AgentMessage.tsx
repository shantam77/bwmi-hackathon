import type {
  AlertProps,
  ChatMessage,
  DecisionBlockProps,
  OptionCardProps,
  PaymentSheetProps,
  PNRConfirmationProps,
} from "@/lib/types";
import AlertMessage from "./AlertMessage";
import DecisionBlock from "./DecisionBlock";
import OptionCard from "./OptionCard";
import PaymentSheet from "./PaymentSheet";
import PNRConfirmation from "./PNRConfirmation";

export default function AgentMessage({
  message,
  onSendMessage,
  disabled,
}: {
  message: ChatMessage;
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}) {
  const component = message.component;

  // Alerts are visually distinct from ordinary replies (PDD section 7) --
  // full width, severity-colored left border, no chat-bubble treatment.
  if (component?.component === "AlertMessage") {
    return (
      <div className="w-full max-w-[85%] self-start">
        <AlertMessage props={component.props as unknown as AlertProps} />
      </div>
    );
  }

  // DecisionBlock is Flow H's flagship moment -- full width, not confined
  // to the usual chat-bubble width, so both option panels have room.
  if (component?.component === "DecisionBlock") {
    return (
      <div className="w-full max-w-full self-start">
        <DecisionBlock
          {...(component.props as unknown as DecisionBlockProps)}
          onSendMessage={onSendMessage}
        />
      </div>
    );
  }

  return (
    <div className="bg-raised max-w-[85%] self-start rounded px-3 py-2">
      <p className="text-ink whitespace-pre-wrap text-sm">{message.content}</p>

      {component?.component === "OptionCard" && (
        <div className="mt-2">
          <OptionCard {...(component.props as unknown as OptionCardProps)} />
        </div>
      )}

      {component?.component === "PaymentSheet" && (
        <div className="mt-2">
          <PaymentSheet
            props={component.props as unknown as PaymentSheetProps}
            onConfirm={() => onSendMessage("Confirm payment")}
            disabled={disabled}
          />
        </div>
      )}

      {component?.component === "PNRConfirmation" && (
        <div className="mt-2">
          <PNRConfirmation {...(component.props as unknown as PNRConfirmationProps)} />
        </div>
      )}
    </div>
  );
}
