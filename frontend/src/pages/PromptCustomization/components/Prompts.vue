<template>
    <div class="h-full overflow-y-auto -mr-6">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl font-bold">{{ $t("promptCustomization.title") }}</h1>
            <div class="flex space-x-4">
                <a
                    href="https://discord.com/invite/JxbPZNDd"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900"
                >
                    <svg class="w-5 h-5 mr-2" role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path
                            d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"
                        />
                    </svg>
                    {{ $t("promptCustomization.joinDiscord") }}
                </a>
                <a
                    href="https://github.com/aomail-ai/aomail-app/issues/new?template=feature-request.yml"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900"
                >
                    <svg class="w-5 h-5 mr-2" role="img" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path
                            d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"
                        />
                    </svg>
                    {{ $t("promptCustomization.submitFeatureRequest") }}
                </a>
                <button
                    @click="resetToDefault"
                    :title="$t('promptCustomization.resetAll')"
                    class="rounded-md bg-gray-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:ring-gray-800"
                >
                    {{ $t("promptCustomization.resetAll") }}
                </button>
                <button
                    @click="saveLLMSettings"
                    class="rounded-md bg-gray-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:ring-gray-800"
                >
                    {{ $t("promptCustomization.saveLLMSettings") }}
                </button>
            </div>
        </div>

        <div class="grid grid-cols-3 gap-4 mb-6">
            <div>
                <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                                <path
                                    fill-rule="evenodd"
                                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                    clip-rule="evenodd"
                                />
                            </svg>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-yellow-800">
                                {{ $t("promptCustomization.importantNotice.title") }}
                            </h3>
                            <div class="mt-2 text-sm text-yellow-700">
                                <ul class="space-y-1">
                                    <li>• {{ $t("promptCustomization.importantNotice.bulletPoints.tested") }}</li>
                                    <li>• {{ $t("promptCustomization.importantNotice.bulletPoints.risk") }}</li>
                                    <li>• {{ $t("promptCustomization.importantNotice.bulletPoints.playground") }}</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-2">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            {{ $t("promptCustomization.llmSettings.provider.label") }}
                        </label>
                        <div class="bg-white p-4 rounded-lg border border-gray-200">
                            <multiselect
                                v-model="llmProvider"
                                :options="llmProviderOptions"
                                track-by="provider"
                                label="provider"
                                :searchable="false"
                                :close-on-select="true"
                                :show-labels="false"
                                :placeholder="$t('promptCustomization.llmSettings.provider.label')"
                                class="mb-2"
                                @select="changeProvider"
                            />
                            <div class="mt-2 text-sm text-gray-600">
                                <p>
                                    <span class="font-medium">
                                        {{ $t("promptCustomization.llmSettings.provider.description") }}
                                    </span>
                                    {{ llmProvider.description }}
                                </p>
                                <p class="mt-1">
                                    <span class="font-medium">
                                        {{ $t("promptCustomization.llmSettings.provider.headquarters") }}
                                    </span>
                                    {{ llmProvider.headquarters }}
                                </p>
                                <p class="mt-1">
                                    <span class="font-medium">
                                        {{ $t("promptCustomization.llmSettings.provider.apiReference") }}
                                    </span>
                                    <a
                                        :href="llmProvider.apiReference"
                                        target="_blank"
                                        class="text-blue-600 hover:text-blue-800 ml-1"
                                    >
                                        {{ $t("promptCustomization.llmSettings.provider.viewDocs") }}
                                    </a>
                                </p>
                            </div>
                        </div>
                    </div>

                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">
                            {{ $t("promptCustomization.llmSettings.model.label") }}
                        </label>
                        <div class="bg-white p-4 rounded-lg border border-gray-200">
                            <multiselect
                                v-model="llmModel"
                                :options="llmModelOptions"
                                label="name"
                                :searchable="false"
                                :close-on-select="true"
                                :show-labels="false"
                                :placeholder="$t('promptCustomization.llmSettings.model.label')"
                                class="mb-2"
                            />
                            <p class="mt-2 text-sm text-gray-600">
                                <span class="font-medium">
                                    {{ $t("promptCustomization.llmSettings.model.description") }}
                                </span>
                                {{ llmModel.description }}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="flex gap-6 h-full pr-4">
            <div class="w-2/5 bg-white rounded-lg p-4 overflow-y-auto max-h-full">
                <h2 class="text-lg font-semibold mb-4">{{ $t("promptCustomization.prompts.title") }}</h2>
                <div class="space-y-4">
                    <div
                        v-for="prompt in Object.keys(customizablePrompts)"
                        :key="prompt"
                        class="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                        :class="{ 'bg-blue-50 border-blue-500': editingPrompt === prompt }"
                        @click="setEditingPrompt(prompt)"
                    >
                        <h3 class="font-medium text-gray-900">
                            {{ $t(`promptCustomization.promptTypes.${prompt}.name`) }}
                        </h3>
                        <p class="text-sm text-gray-500 mt-1">
                            {{ $t(`promptCustomization.promptTypes.${prompt}.description`) }}
                        </p>
                        <div class="mt-2">
                            <span class="text-xs text-gray-500">
                                {{ $t("promptCustomization.prompts.requiredVariables") }}
                            </span>
                            <div class="flex flex-wrap gap-1 mt-1">
                                <span
                                    v-for="variable in customizablePrompts[prompt].variables"
                                    :key="variable"
                                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800"
                                >
                                    {{ variable }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="flex-1 bg-white rounded-lg p-4">
                <div class="space-y-6">
                    <div v-if="editingPrompt" class="mb-6">
                        <div class="flex justify-between items-center mb-4">
                            <h2 class="text-lg font-semibold">
                                {{ $t("promptCustomization.prompts.editing") }}
                                {{ $t(`promptCustomization.promptTypes.${editingPrompt}.name`) }}
                            </h2>
                            <div class="flex space-x-2">
                                <button
                                    @click="resetSelectedPrompt"
                                    class="rounded-md bg-gray-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:ring-gray-800"
                                >
                                    {{ $t("promptCustomization.prompts.resetSelected") }}
                                </button>
                            </div>
                        </div>

                        <div class="space-y-4">
                            <div v-if="editingPrompt" class="bg-orange-50 border-l-4 border-orange-400 p-4 mb-4">
                                <div class="flex">
                                    <div class="flex-shrink-0">
                                        <svg class="h-5 w-5 text-orange-400" viewBox="0 0 20 20" fill="currentColor">
                                            <path
                                                fill-rule="evenodd"
                                                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                                clip-rule="evenodd"
                                            />
                                        </svg>
                                    </div>
                                    <div class="ml-3">
                                        <p class="text-sm text-orange-700">
                                            {{ $t("promptCustomization.prompts.formatWarning") }}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div class="space-y-4">
                                <textarea
                                    v-model="promptInput"
                                    class="w-full h-96 px-4 py-3 rounded-lg border border-gray-300 focus:ring-blue-500 focus:border-blue-500"
                                    :placeholder="$t('promptCustomization.prompts.placeholder')"
                                />

                                <div class="flex justify-end">
                                    <button
                                        @click="savePrompt"
                                        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                                    >
                                        {{ $t("promptCustomization.prompts.saveChanges") }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div v-else class="flex items-center justify-center h-full text-gray-500">
                        {{ $t("promptCustomization.prompts.selectPrompt") }}
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { deleteData, getData, putData } from "@/global/fetchData";
import { inject, onMounted, ref, computed } from "vue";
import Multiselect from "vue-multiselect";
import { i18n } from "@/global/preferences";

interface Prompt {
    prompt: string;
    variables: string[];
}

interface LLMModel {
    name: string;
    description: string;
}

interface LLMProvider {
    provider: string;
    headquarters: string;
    apiReference: string;
    description: string;
    models: LLMModel[];
}

const llmProviderOptions: LLMProvider[] = [
    {
        provider: "google",
        headquarters: "Mountain View, CA, USA",
        apiReference: "https://ai.google.dev/gemini-api/docs/models/gemini",
        description: "Google's AI model provider",
        models: [
            {
                name: "gemini-1.5-pro",
                description:
                    "Most capable model for highly complex tasks, with improved performance in coding, math, and reasoning. Supports text, images, and function calling.",
            },
            {
                name: "gemini-2.0-flash",
                description:
                    "Latest model optimized for speed and efficiency. Best for real-time applications requiring fast responses while maintaining high quality output.",
            },
        ],
    },
    {
        provider: "openai",
        headquarters: "San Francisco, CA, USA",
        apiReference: "https://platform.openai.com/docs/models#gpt-4o",
        description: "OpenAI's AI model provider",
        models: [
            {
                name: "gpt-4o-mini",
                description:
                    "Most capable multimodal model, optimized for both vision and language tasks. Excels at complex reasoning and creative generation.",
            },
        ],
    },
    {
        provider: "anthropic",
        headquarters: "San Francisco, CA, USA",
        description: "Anthropic's AI model provider",
        apiReference: "https://docs.anthropic.com/en/docs/about-claude/models/all-models",
        models: [
            {
                name: "claude-3-5-haiku-latest",
                description:
                    "Fastest and most cost-effective Claude model. Optimized for quick responses while maintaining high accuracy on common tasks.",
            },
        ],
    },
    {
        provider: "mistral",
        headquarters: "Paris, France",
        description: "Mistral's AI model provider",
        apiReference: "https://docs.mistral.ai/getting-started/models/models_overview/",
        models: [
            {
                name: "ministral-8b-latest",
                description:
                    "Efficient 8B parameter model optimized for edge deployment. Excellent performance-to-size ratio for local inference.",
            },
            {
                name: "mistral-small-latest",
                description:
                    "Compact but powerful model with strong reasoning capabilities. Ideal for production deployments requiring balance of speed and quality.",
            },
        ],
    },
    {
        provider: "groq",
        headquarters: "Mountain View, CA, USA",
        description: "Groq's AI model provider",
        apiReference: "https://console.groq.com/docs/api-reference",
        models: [
            {
                name: "llama3-8b-8192",
                description: "Most capable model from Meta AI",
            },
        ],
    },
    {
        provider: "deepseek",
        headquarters: "Hangzhou, Zhejiang, China",
        description: "DeepSeek's AI model provider",
        apiReference: "https://deepseek.com/docs/api-reference",
        models: [
            {
                name: "deepseek-chat",
                description: "Default model for general purpose tasks",
            },
        ],
    },
];

const promptInput = ref("");

function changeProvider() {
    llmModel.value = llmProvider.value.models[0];
}
const llmModel = ref<LLMModel>(llmProviderOptions[0].models[0]);
const llmProvider = ref<LLMProvider>(llmProviderOptions[0]);
const llmModelOptions = computed(() => {
    const provider = llmProviderOptions.find((p) => p.provider === llmProvider.value.provider);
    return provider ? provider.models : [];
});

const displayPopup = inject<(type: "success" | "error", title: string, message: string) => void>("displayPopup");

const customizablePrompts = ref<{ [key: string]: Prompt }>({});

const editingPrompt = ref<string | null>(null);

async function resetToDefault() {
    llmModel.value = llmProviderOptions[0].models[0];
    llmProvider.value = llmProviderOptions[0];
    promptInput.value = "";
    editingPrompt.value = null;

    const result = await deleteData("user/preferences/llm_settings/", { resetAll: true });

    if (!result.success) {
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.resetError"),
            result.error as string
        );
        return;
    }

    displayPopup?.(
        "success",
        i18n.global.t("constants.popUpConstants.successMessages.resetSuccess"),
        i18n.global.t("constants.popUpConstants.successMessages.resetSuccessDesc")
    );

    await fetchLLMSettings();
}

async function resetSelectedPrompt() {
    const result = await deleteData("user/preferences/llm_settings/", {
        [editingPrompt.value as string]: true,
    });

    if (!result.success) {
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.resetSelectedError"),
            result.error as string
        );
        return;
    }

    displayPopup?.(
        "success",
        i18n.global.t("constants.popUpConstants.successMessages.resetSelectedSuccess"),
        i18n.global.t("constants.popUpConstants.successMessages.resetSelectedSuccessDesc")
    );

    await fetchLLMSettings();

    if (editingPrompt.value) {
        promptInput.value = customizablePrompts.value[editingPrompt.value].prompt || "";
    }
}

async function saveLLMSettings() {
    const result = await putData("user/preferences/llm_settings/", {
        llmProvider: llmProvider.value.provider,
        llmModel: llmModel.value.name,
    });

    if (!result.success) {
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.saveLLMSettingsError"),
            result.error as string
        );
        return;
    }

    displayPopup?.(
        "success",
        i18n.global.t("constants.popUpConstants.successMessages.saveLLMSettingsSuccess"),
        i18n.global.t("constants.popUpConstants.successMessages.saveLLMSettingsSuccessDesc")
    );

    await fetchLLMSettings();
}

async function savePrompt() {
    if (!editingPrompt.value) {
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.noPromptSelected"),
            i18n.global.t("constants.popUpConstants.errorMessages.noPromptSelectedDesc")
        );
        return;
    }

    const promptData = customizablePrompts.value[editingPrompt.value];
    const missingVariables = promptData.variables.filter((variable) => !promptInput.value.includes(`{${variable}}`));

    if (missingVariables.length > 0) {
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.missingVariables"),
            i18n.global.t("constants.popUpConstants.errorMessages.missingVariablesDesc", {
                variables: missingVariables.join(", "),
            })
        );
        return;
    }

    const result = await putData("user/preferences/llm_settings/", {
        [editingPrompt.value as string]: promptInput.value,
    });

    if (!result.success) {
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.savePromptError"),
            result.error as string
        );
        return;
    }

    displayPopup?.(
        "success",
        i18n.global.t("constants.popUpConstants.successMessages.promptSaved"),
        i18n.global.t("constants.popUpConstants.successMessages.promptSavedDesc")
    );
}

function setEditingPrompt(promptName: string) {
    editingPrompt.value = promptName;
    promptInput.value = customizablePrompts.value[promptName].prompt || "";
}

async function fetchLLMSettings() {
    const result = await getData("user/preferences/llm_settings/");
    if (!result.success) {
        displayPopup?.("error", "Failed to fetch LLM settings", result.error as string);
        return;
    }

    const data = result.data;

    llmProvider.value = llmProviderOptions.find((p) => p.provider === data.llmProvider) || llmProviderOptions[0];
    llmModel.value = llmModelOptions.value.find((m) => m.name === data.llmModel) || llmModelOptions.value[0];

    delete data.llmProvider;
    delete data.llmModel;
    customizablePrompts.value = data;
}

onMounted(async () => {
    await fetchLLMSettings();
    document.addEventListener("keydown", (event) => {
        if (event.ctrlKey && event.key === "s") {
            event.preventDefault();

            saveLLMSettings();

            if (editingPrompt.value) {
                savePrompt();
            }
        }
    });
});
</script>
