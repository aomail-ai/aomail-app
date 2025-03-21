<template>
    <div v-if="isModalOpen" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
        <div class="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <NotificationTimer
                :showNotification="showNotification"
                :notificationTitle="notificationTitle"
                :notificationMessage="notificationMessage"
                :backgroundColor="backgroundColor"
                @dismissPopup="dismissPopup"
            />
            <h1 class="text-2xl mb-6">{{ $t("passwordReset.title") }}</h1>
            <p class="text-lg mb-6">{{ $t("passwordReset.newPasswordInstructions") }}</p>
            <form @submit.prevent="resetPassword">
                <div class="mb-6">
                    <label for="password" class="block font-bold mb-2">{{ $t("passwordReset.password") }}</label>
                    <div class="relative items-stretch mt-2 flex">
                        <input
                            ref="passwordInput"
                            :type="showPassword ? 'text' : 'password'"
                            id="password"
                            v-model="password"
                            required
                            class="flex-1 rounded-l-md border-0 pl-3 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-gray-800 sm:text-sm sm:leading-6"
                        />
                        <div class="flex items-center">
                            <button
                                @click.prevent="togglePasswordVisibility"
                                class="p-2 bg-gray-50 rounded-r-md ring-l-none ring-1 ring-inset ring-gray-300"
                            >
                                <svg class="w-6 h-6" stroke="currentColor">
                                    <use :href="eyeIcon + '#' + (showPassword ? 'eye-hidden' : 'eye-visible')" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
                <div class="mb-6">
                    <label for="confirmPassword" class="block font-bold mb-2">
                        {{ $t("passwordReset.confirmPassword") }}
                    </label>
                    <div class="relative items-stretch mt-2 flex">
                        <input
                            ref="confirmPasswordInput"
                            :type="showConfirmPassword ? 'text' : 'password'"
                            id="confirmPassword"
                            v-model="confirmPassword"
                            required
                            class="flex-1 rounded-l-md border-0 pl-3 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-gray-800 sm:text-sm sm:leading-6"
                        />
                        <div class="flex items-center">
                            <button
                                @click.prevent="toggleConfirmPasswordVisibility"
                                class="p-2 bg-gray-50 rounded-r-md ring-l-none ring-1 ring-inset ring-gray-300"
                            >
                                <svg class="w-6 h-6" stroke="currentColor">
                                    <use :href="eyeIcon + '#' + (showConfirmPassword ? 'eye-hidden' : 'eye-visible')" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
                <button type="submit" class="w-full py-2 bg-black text-white rounded hover:bg-gray-800 transition">
                    {{ $t("constants.userActions.submit") }}
                </button>
            </form>
        </div>
    </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted } from "vue";
import NotificationTimer from "@/global/components/NotificationTimer.vue";
import { API_BASE_URL, PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH } from "@/global/const";
import { displayErrorPopup, displaySuccessPopup } from "@/global/popUp";
import router from "@/router/router";
import { i18n } from "@/global/preferences";
import eyeIcon from "@/assets/eye-icon.svg";

const isModalOpen = ref(true);
const password = ref<string>("");
const confirmPassword = ref<string>("");
const uidb64 = ref<string>("");
const token = ref<string>("");
const passwordInput = ref<HTMLInputElement | null>(null);
const confirmPasswordInput = ref<HTMLInputElement | null>(null);
const showPassword = ref<boolean>(false);
const showConfirmPassword = ref<boolean>(false);

const showNotification = ref<boolean>(false);
const notificationTitle = ref<string>("");
const notificationMessage = ref<string>("");
const backgroundColor = ref<string>("");
const timerId = ref<number | null>(null);

function togglePasswordVisibility() {
    showPassword.value = !showPassword.value;
}

function toggleConfirmPasswordVisibility() {
    showConfirmPassword.value = !showConfirmPassword.value;
}

const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter") {
        event.preventDefault();
        resetPassword();
    }

    if (event.key === "Tab") {
        event.preventDefault();
        if (!password.value) {
            passwordInput.value?.focus();
        } else if (!confirmPassword.value) {
            confirmPasswordInput.value?.focus();
        } else {
            if (document.activeElement === passwordInput.value) {
                confirmPasswordInput.value?.focus();
            } else {
                passwordInput.value?.focus();
            }
        }
    }
};

onMounted(() => {
    document.addEventListener("keydown", handleKeyDown);
    const urlParams = new URLSearchParams(window.location.search);
    uidb64.value = urlParams.get("uidb64") || "";
    token.value = urlParams.get("token") || "";

    if (!uidb64.value || !token.value) {
        router.push({ name: "login" });
    }
});

onUnmounted(() => {
    document.removeEventListener("keydown", handleKeyDown);
});

function dismissPopup() {
    showNotification.value = false;
    if (timerId.value) {
        clearTimeout(timerId.value);
    }
}

function displayPopup(type: "success" | "error", title: string, message: string) {
    if (type === "error") {
        displayErrorPopup(showNotification, notificationTitle, notificationMessage, backgroundColor, title, message);
    } else {
        displaySuccessPopup(showNotification, notificationTitle, notificationMessage, backgroundColor, title, message);
    }
    timerId.value = setTimeout(dismissPopup, 4000);
}

async function resetPassword() {
    if (password.value.length < PASSWORD_MIN_LENGTH || password.value.length > PASSWORD_MAX_LENGTH) {
        displayPopup(
            "error",
            i18n.global.t("passwordReset.invalidInput"),
            i18n.global.t("passwordReset.passwordLengthError")
        );
        return;
    }

    if (password.value !== confirmPassword.value) {
        displayPopup(
            "error",
            i18n.global.t("passwordReset.invalidInput"),
            i18n.global.t("passwordReset.passwordsDoNotMatch")
        );
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}reset_password/${uidb64.value}/${token.value}/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ password: password.value }),
        });

        if (response.ok) {
            displayPopup(
                "success",
                i18n.global.t("constants.successMessages.success"),
                i18n.global.t("passwordReset.resetSuccessful")
            );
            setTimeout(() => {
                router.push({ name: "login" });
            }, 3000);
        } else {
            const data = await response.json();
            displayPopup(
                "error",
                i18n.global.t("passwordReset.invalidInput"),
                data.error || i18n.global.t("passwordReset.genericError")
            );
        }
    } catch (error) {
        displayPopup(
            "error",
            i18n.global.t("passwordReset.invalidInput"),
            (error as Error).message || i18n.global.t("passwordReset.genericError")
        );
    }
}
</script>
