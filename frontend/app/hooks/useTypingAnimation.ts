import { useState, useEffect, useMemo } from "react";

export const useTypingAnimation = (texts: string[], searchValue: string) => {
    const [currentPlaceholderIndex, setCurrentPlaceholderIndex] = useState(0);
    const [typedText, setTypedText] = useState("");
    const [isTyping, setIsTyping] = useState(true);
    const [isDeleting, setIsDeleting] = useState(false);

    // typing animation logic
    
    return { typedText, isTyping, isDeleting };
};