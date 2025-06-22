import { useState, useEffect } from "react";

export const useTypingAnimation = (texts: string[], searchValue: string) => {
    const [currentPlaceholderIndex, setCurrentPlaceholderIndex] = useState(0);
    const [typedText, setTypedText] = useState("");
    const [isTyping, setIsTyping] = useState(true);
    const [isDeleting, setIsDeleting] = useState(false);

    // Typing animation effect
    useEffect(() => {
        if (searchValue.trim()) {
            setTypedText("");
            return; // Don't animate when user is typing
        }

        const currentText = texts[currentPlaceholderIndex];
        let timeout: NodeJS.Timeout;

        if (isTyping && !isDeleting) {
            // Typing characters
            if (typedText.length < currentText.length) {
                timeout = setTimeout(() => {
                    setTypedText(currentText.slice(0, typedText.length + 1));
                }, 25 + Math.random() * 50); // Variable typing speed (25-75ms) - twice as fast
            } else {
                // Finished typing, wait then start deleting
                timeout = setTimeout(() => {
                    setIsDeleting(true);
                }, 2000); // Pause for 2 seconds when done typing
            }
        } else if (isDeleting) {
            // Deleting characters
            if (typedText.length > 0) {
                timeout = setTimeout(() => {
                    setTypedText(typedText.slice(0, -1));
                }, 15 + Math.random() * 25); // Faster deleting (15-40ms) - twice as fast
            } else {
                // Finished deleting, move to next placeholder
                setIsDeleting(false);
                setCurrentPlaceholderIndex((prev) => (prev + 1) % texts.length);
                setTimeout(() => {
                    setIsTyping(true);
                }, 300); // Short pause before starting next text
            }
        }

        return () => clearTimeout(timeout);
    }, [searchValue, typedText, isTyping, isDeleting, currentPlaceholderIndex, texts]);

    // Return the animated placeholder text with cursor
    const animatedPlaceholder = typedText + (isTyping && !isDeleting ? "|" : "");
    
    return { animatedPlaceholder };
};