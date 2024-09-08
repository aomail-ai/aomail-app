import { ALLOWED_LANGUAGES, ALLOWED_THEMES, UNAUTHENTICATED_URLS } from "./const";
import { ref } from "vue";
import { createI18n, I18n } from "vue-i18n";
import messages from "@/i18n";
import { getData } from "./fetchData";

type UserPreferenceResponse = {
    language?: string;
    theme?: string;
    timezone?: string;
    error?: string;
};

const languageSelected = ref("american");
export const themeSelected = ref("light");
export const timezoneSelected = ref("UTC");

export const formatSentDateAndTime = (sentDateString: string, sentTimeString: string) => {
    const sentDateAndTimeString = `${sentDateString}T${sentTimeString}:00Z`;
    const sentDateObject = new Date(sentDateAndTimeString);

    const formattedSentDateAndTime = sentDateObject.toLocaleString(i18n.global.locale, {
        timeZone: timezoneSelected.value,
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });

    return formattedSentDateAndTime;
};

export const formatSentDate = (sentDateString: string) => {
    const sentDateObject = new Date(`${sentDateString}T00:00:00Z`);

    const formattedSentDate = sentDateObject.toLocaleDateString(i18n.global.locale, {
        timeZone: timezoneSelected.value,
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
    });

    return formattedSentDate;
};

export const formatSentTime = (sentDateString: string, sentTimeString: string) => {
    const sentDateTimeString = `${sentDateString}T${sentTimeString}:00Z`;
    const sentDateTimeObject = new Date(sentDateTimeString);

    const formattedSentTime = sentDateTimeObject.toLocaleTimeString(i18n.global.locale, {
        timeZone: timezoneSelected.value,
        hour: "2-digit",
        minute: "2-digit",
    });

    return formattedSentTime;
};

const fetchUserPreference = async (
    endpoint: string,
    key: keyof UserPreferenceResponse,
    allowedValues?: string[]
): Promise<string | null> => {
    const storedValue = localStorage.getItem(key);

    if (storedValue && allowedValues?.includes(storedValue)) {
        return storedValue;
    }

    const result = await getData(`${endpoint}`);

    if (!result.success) {
        return null;
    }

    if (result.data[key] !== undefined) {
        const value = result.data[key];
        if (typeof value === "string") {
            localStorage.setItem(key, value);
            return value;
        }
    }

    return null;
};

const isUnAuthenticatedUrl = (url: string) => {
    return UNAUTHENTICATED_URLS.some((baseUrl) => url.split("?")[0] === baseUrl);
};

export const initializePreferences = async (i18n: I18n) => {
    const currentUrl = window.location.href;

    if (!isUnAuthenticatedUrl(currentUrl)) {
        const language = await fetchUserPreference("user/preferences/language/", "language", [...ALLOWED_LANGUAGES]);
        if (language) {
            languageSelected.value = language;
            i18n.global.locale = language;
        }
        const theme = await fetchUserPreference("user/preferences/theme/", "theme", ALLOWED_THEMES);
        if (theme) {
            themeSelected.value = theme;
        }
        const timezone = await fetchUserPreference("user/preferences/timezone/", "timezone");
        if (timezone) {
            timezoneSelected.value = timezone;
        }
    }
};

export const i18n = createI18n({ legacy: true, locale: languageSelected.value, fallbackLocale: "american", messages });
