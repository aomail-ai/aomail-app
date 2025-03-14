<template>
    <transition name="modal-fade">
        <Modal
            v-if="props.isOpen"
            @click.self="closeModal"
            class="fixed z-[250] top-0 left-0 w-full h-full bg-black bg-opacity-50 flex items-center justify-center"
        >
            <div class="bg-white rounded-lg relative w-[450px]">
                <div class="absolute right-0 top-0 hidden pr-4 pt-4 sm:block p-8">
                    <button
                        @click="closeModal"
                        type="button"
                        class="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
                    >
                        <XMarkIcon class="h-6 w-6" aria-hidden="true" />
                    </button>
                </div>
                <div class="flex items-center w-full h-16 bg-gray-50 ring-1 ring-black ring-opacity-5 rounded-t-lg">
                    <div class="ml-8 flex items-center space-x-1">
                        <p class="block leading-6 text-gray-900 font-medium">
                            {{ $t("constants.categoryModalConstants.addCategory") }}
                        </p>
                    </div>
                </div>
                <div class="flex flex-col gap-4 px-8 py-6">
                    <p class="text-red-500" v-if="errorMessage">{{ errorMessage }}</p>
                    <div>
                        <label for="categoryName" class="block text-sm font-medium leading-6 text-gray-900">
                            {{ $t("constants.categoryModalConstants.categoryName") }}
                        </label>
                        <div class="mt-2">
                            <input
                                id="newCategoryName"
                                v-model="categoryName"
                                class="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-gray-600 sm:text-sm sm:leading-6"
                                :placeholder="$t('constants.categoryModalConstants.administrative')"
                            />
                        </div>
                    </div>
                    <div>
                        <label for="categoryDescription" class="block text-sm font-medium leading-6 text-gray-900">
                            {{ $t("constants.categoryModalConstants.categoryDescription") }}
                        </label>
                        <div class="mt-2">
                            <textarea
                                id="newCategoryDescription"
                                v-model="categoryDescription"
                                rows="3"
                                style="min-height: 60px"
                                class="block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-gray-600 sm:text-sm sm:leading-6"
                            ></textarea>
                        </div>
                        <p class="mt-3 text-sm leading-6 text-gray-600">
                            {{ $t("constants.categoryModalConstants.categoryDescriptionExplanation") }}
                        </p>
                    </div>
                    <div class="mt-2 sm:mt-2 sm:flex sm:flex-row-reverse">
                        <button
                            type="button"
                            class="inline-flex w-full rounded-md bg-gray-800 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-black sm:w-auto"
                            @click="addCategory"
                        >
                            {{ $t("constants.userActions.create") }}
                        </button>
                    </div>
                </div>
            </div>
        </Modal>
    </transition>
</template>

<script setup lang="ts">
import { Ref, ref, inject, onMounted, onUnmounted } from "vue";
import { i18n } from "@/global/preferences";
import { postData } from "@/global/fetchData";
import { XMarkIcon } from "@heroicons/vue/20/solid";
import { Category } from "@/global/types";
import { createDefaultFilters } from "@/global/filters";

const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        addCategory();
    } else if (event.key === "Escape") {
        event.preventDefault();
        closeModal();
    } else if (event.key === "Tab") {
        event.preventDefault();
        const target = document.activeElement as HTMLElement;

        const categoryNameElement = document.getElementById("newCategoryName") as HTMLInputElement;
        const categoryDescriptionElement = document.getElementById("newCategoryDescription") as HTMLInputElement;

        if (!categoryName.value) {
            categoryNameElement?.focus();
        } else if (!categoryDescription.value) {
            categoryDescriptionElement?.focus();
        } else if (target.id === "newCategoryDescription") {
            categoryNameElement?.focus();
        } else {
            categoryDescriptionElement?.focus();
        }
    }
};

onMounted(() => {
    document.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
    document.removeEventListener("keydown", handleKeyDown);
});

const props = defineProps<{
    isOpen: boolean;
}>();

const emit = defineEmits<{
    (e: "close"): void;
    (e: "categoryCreated"): void;
    (e: "selectCategory", category: Category): void;
}>();

const displayPopup = inject<(type: "success" | "error", title: string, message: string) => void>("displayPopup");
const fetchCategoriesAndTotals = inject("fetchCategoriesAndTotals") as () => Promise<void>;
const fetchFiltersData = inject("fetchFiltersData") as (category: string) => Promise<void>;
const fetchEmailsData = inject("fetchEmailsData") as (category: string) => Promise<void>;
const categories = inject("categories") as Ref<Category[]>;
const selectedCategory = inject("selectedCategory") as Ref<string>;

const categoryName = ref("");
const categoryDescription = ref("");
const errorMessage = ref("");

const closeModal = () => {
    emit("close");
    resetForm();
};

const resetForm = () => {
    categoryName.value = "";
    categoryDescription.value = "";
    errorMessage.value = "";
};

const addCategory = async () => {
    if (!props.isOpen) {
        return;
    }

    if (!categoryName.value.trim() || !categoryDescription.value.trim()) {
        errorMessage.value = i18n.global.t("homePage.modals.pleaseFillAllFields");
        return;
    }

    if (categoryName.value.length > 50) {
        errorMessage.value = i18n.global.t("homePage.modals.newCategoryModal.maxNameCharacters");
        return;
    }

    if (categoryDescription.value.length > 300) {
        errorMessage.value = i18n.global.t("homePage.modals.newCategoryModal.maxDescriptionCharacters");
        return;
    }

    const result = await postData(`create_categories/`, {
        categories: [
            {
                name: categoryName.value,
                description: categoryDescription.value,
            },
        ],
    });
    if (result.success) {
        emit("selectCategory", {
            name: categoryName.value,
            description: categoryDescription.value,
        });
        selectedCategory.value = categoryName.value;
        categories.value.push({
            name: categoryName.value,
            description: categoryDescription.value,
        });

        await createDefaultFilters(categoryName.value);

        await fetchCategoriesAndTotals();
        await fetchFiltersData(categoryName.value);
        await fetchEmailsData(categoryName.value);

        closeModal();
        displayPopup?.(
            "success",
            i18n.global.t("constants.popUpConstants.successMessages.success"),
            i18n.global.t("constants.popUpConstants.successMessages.categoryAddedSuccess")
        );
    } else {
        closeModal();
        displayPopup?.(
            "error",
            i18n.global.t("constants.popUpConstants.errorMessages.addCategoryError"),
            result.error as string
        );
    }
};
</script>
