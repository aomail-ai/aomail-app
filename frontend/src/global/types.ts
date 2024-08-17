import { Component as VueComponent } from "vue";

export interface KeyValuePair {
    key: string;
    value: string;
}

export interface EmailSender {
    id?: number;
    username: string;
    email: string;
}

export interface Category {
    name: string;
    description: string;
}

export interface NavigationPage {
    name: string;
    href: string;
    icon: VueComponent;
    current?: boolean;
}

interface Sender {
    email: string;
    name: string;
}

interface EmailRule {
    hasRule: boolean;
    ruleId: number;
}

interface EmailAttachment {
    attachmentName: string;
    attachmentId: number;
}

interface EmailFlags {
    spam: boolean;
    scam: boolean;
    newsletter: boolean;
    notification: boolean;
    meeting: boolean;
}

export interface FetchDataResult {
    success: boolean;
    data?: any;
    error?: string;
}

export interface Contact {
    id: number;
    email: string;
    username: string;
    providerId: string;
}

export interface Recipient {
    email: string;
}

export interface Email {
    id: number;
    subject: string;
    sender: Sender;
    providerId: string;
    shortSummary: string;
    oneLineSummary: string;
    cc: Sender[];
    bcc: Sender[];
    read: boolean;
    answerLater: boolean;
    rule: EmailRule;
    hasAttachments: boolean;
    attachments: EmailAttachment[];
    sentDate: string | null;
    sentTime: string | null;
    answer: boolean;
    relevance: string;
    priority: string;
    flags: EmailFlags;
    category?: string;
    htmlContent?: string;
}

export interface EmailDetails {
    data: {
        [category: string]: {
            [priority: string]: Email[];
        };
    };
}

export interface AttachmentType {
    extension: string;
    name: string;
}

export interface EmailLinked {
    email: string;
    typeApi: string;
}

export interface UploadedFile {
    name: string;
    size: number;
}
