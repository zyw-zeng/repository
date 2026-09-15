/** 此文件由 FastAPI /openapi.json 自动生成，请勿手工编辑。 */

export interface paths {
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 检查应用是否存活
         * @description 确认 Web 进程能够正常响应请求。
         */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 检查本地依赖是否就绪
         * @description 检查 SQLite、原始文档目录和 Chroma，不会调用远程模型或产生费用。
         */
        get: operations["readiness_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 管理员登录
         * @description 校验环境变量中的管理员密码并签发短期令牌。
         */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 验证管理员登录状态
         * @description 令牌验证通过后返回最小管理员身份信息。
         */
        get: operations["get_current_admin_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 分页获取文档列表
         * @description 分页返回已上传文档及其处理状态。
         */
        get: operations["list_documents_api_v1_documents_get"];
        put?: never;
        /**
         * 上传文档并创建索引任务
         * @description 支持 PDF、Markdown、TXT 和 DOCX。上传成功后返回文档与任务，客户端应使用任务 ID 查询进度。
         */
        post: operations["upload_document_api_v1_documents_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 获取文档详情
         * @description 返回指定文档的状态和活动索引版本。
         */
        get: operations["get_document_api_v1_documents__document_id__get"];
        put?: never;
        post?: never;
        /**
         * 创建文档删除任务
         * @description 后台依次删除向量、原始文件和数据库记录，操作可以在中断后恢复。
         */
        delete: operations["delete_document_api_v1_documents__document_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/documents/{document_id}/visibility": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /**
         * 修改文档公开范围
         * @description 只有 public 文档会进入访客知识问答和 Agent 工具结果。
         */
        patch: operations["update_document_visibility_api_v1_documents__document_id__visibility_patch"];
        trace?: never;
    };
    "/api/v1/documents/{document_id}/reindex": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 创建文档重新索引任务
         * @description 新索引全部成功前继续使用旧活动版本，避免重建失败影响查询。
         */
        post: operations["reindex_document_api_v1_documents__document_id__reindex_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingestion-jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 分页列出文档处理任务
         * @description 返回刷新页面后仍可查看的任务历史和运行状态。
         */
        get: operations["list_ingestion_jobs_api_v1_ingestion_jobs_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/ingestion-jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 查询文档处理任务
         * @description 前端可定时调用此接口，直到状态变为 completed 或 failed。
         */
        get: operations["get_ingestion_job_api_v1_ingestion_jobs__job_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/chat/query": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 执行知识库问答或闲聊
         * @description knowledge_base 模式强制执行查询改写、向量检索和引用校验；没有可靠依据时返回 grounded=false。casual 模式不查询知识库。
         */
        post: operations["query_knowledge_api_v1_chat_query_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 分页列出会话
         * @description 全局会话可能包含访客历史，因此只向管理员开放。
         */
        get: operations["list_conversations_api_v1_conversations_get"];
        put?: never;
        /**
         * 创建 Agent 会话
         * @description 创建可持久化消息和运行轨迹的会话。
         */
        post: operations["create_conversation_api_v1_conversations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 读取 Agent 会话
         * @description 返回会话元数据和最近 50 条消息。
         */
        get: operations["get_conversation_api_v1_conversations__conversation_id__get"];
        put?: never;
        post?: never;
        /**
         * 删除会话
         * @description 管理员删除会话、历史消息和关联展示数据。
         */
        delete: operations["delete_conversation_api_v1_conversations__conversation_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 发送消息并运行 LangGraph Agent
         * @description Agent 识别意图后只能调用白名单工具。知识检索无依据时允许有限改写重试，达到步骤、时间或递归上限后返回 degraded=true。
         */
        post: operations["send_agent_message_api_v1_conversations__conversation_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{conversation_id}/messages/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 流式发送消息并运行 Agent
         * @description 使用 Server-Sent Events 返回运行开始、Agent 步骤、正式回答片段、引用和完成事件。模型输出不经过额外核验模型等待。
         */
        post: operations["stream_agent_message_api_v1_conversations__conversation_id__messages_stream_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{conversation_id}/runs/{request_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 停止正在执行的 Agent 运行
         * @description 通知模型流和后续 LangGraph 节点尽快停止执行。
         */
        post: operations["cancel_agent_run_api_v1_conversations__conversation_id__runs__request_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jd-analyses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 分析粘贴的岗位 JD
         * @description 同步执行岗位匹配，适合 Swagger 调试和非流式客户端。
         */
        post: operations["analyze_jd_api_v1_jd_analyses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jd-analyses/{analysis_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 读取岗位匹配报告
         * @description 返回刷新页面后仍可恢复的结构化报告。
         */
        get: operations["get_jd_analysis_api_v1_jd_analyses__analysis_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jd-analyses/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 流式分析粘贴的岗位 JD
         * @description 持续发送解析、逐项检索、评价和最终报告事件。
         */
        post: operations["stream_jd_analysis_api_v1_jd_analyses_stream_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jd-analyses/runs/{request_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 取消正在执行的岗位匹配
         * @description 向真实后端任务发送取消信号。
         */
        post: operations["cancel_jd_analysis_api_v1_jd_analyses_runs__request_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/career/conversations/{conversation_id}/materials": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 生成岗位定制求职材料
         * @description 返回自我介绍、项目亮点、面试准备和能力补足计划。
         */
        get: operations["get_career_materials_api_v1_career_conversations__conversation_id__materials_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/career/conversations/{conversation_id}/report": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 下载带引用的求职分析报告
         * @description 下载 UTF-8 Markdown 报告，保留正文与引用之间的可审计关系。
         */
        get: operations["download_career_report_api_v1_career_conversations__conversation_id__report_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/suggestions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 读取首页动态推荐问题
         * @description 根据当前公开知识库主题生成并缓存，文档版本变化后自动使用新缓存。
         */
        get: operations["get_empty_suggestions_api_v1_suggestions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tts/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 流式合成回答语音
         * @description 使用阿里云 CosyVoice 将完整回答转换为 MP3，并按音频块持续返回。
         */
        post: operations["stream_speech_api_v1_tts_stream_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tts/profiles/{character_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 读取角色当前音色
         * @description 供访客端读取是否自动朗读以及当前角色音色。
         */
        get: operations["get_voice_profile_api_v1_tts_profiles__character_id__get"];
        /**
         * 更新角色 CosyVoice 音色
         * @description 管理员更新配置；后续合成请求立即读取新值。
         */
        put: operations["update_voice_profile_api_v1_tts_profiles__character_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tts/profiles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 管理端读取全部角色音色
         * @description 管理员读取星云、比特和沫沫的完整配置。
         */
        get: operations["list_voice_profiles_api_v1_tts_profiles_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/tts/runs/{request_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * 停止正在进行的语音合成
         * @description 按幂等方式取消活动任务；任务已结束时同样安全返回。
         */
        post: operations["cancel_speech_api_v1_tts_runs__request_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 读取公开简历信息
         * @description 返回简历名称、版本、大小以及稳定的预览和下载地址。
         */
        get: operations["get_resume_info_api_v1_resume_get"];
        /**
         * 管理员替换公开简历
         * @description 校验上传内容后原子替换，失败时保留原有公开版本。
         */
        put: operations["replace_resume_api_v1_resume_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resume/download": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 下载当前公开简历
         * @description 以附件形式返回当前简历，由浏览器保存为 PDF。
         */
        get: operations["download_resume_api_v1_resume_download_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/resume/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * 在线预览当前公开简历
         * @description 以内联形式返回当前简历，交给浏览器 PDF 阅读器显示。
         */
        get: operations["preview_resume_api_v1_resume_preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /**
         * AdminLoginRequest
         * @description 管理员登录请求。
         */
        AdminLoginRequest: {
            /**
             * Password
             * @description 管理员密码。
             */
            password: string;
        };
        /**
         * AdminProfileResponse
         * @description 当前管理端身份。
         */
        AdminProfileResponse: {
            /**
             * Role
             * @default admin
             * @constant
             */
            role: "admin";
        };
        /**
         * AdminTokenResponse
         * @description 登录成功后返回的短期访问令牌。
         */
        AdminTokenResponse: {
            /** Access Token */
            access_token: string;
            /**
             * Token Type
             * @default bearer
             * @constant
             */
            token_type: "bearer";
            /**
             * Expires In
             * @description 令牌剩余有效秒数。
             */
            expires_in: number;
        };
        /**
         * AgentCancellationResponse
         * @description 服务端已接收指定 Agent 运行的取消请求。
         */
        AgentCancellationResponse: {
            /** Request Id */
            request_id: string;
            /**
             * Status
             * @default cancellation_requested
             */
            status: string;
        };
        /**
         * AgentExecutionResponse
         * @description Agent 回答、引用、运行状态和精简执行轨迹。
         */
        AgentExecutionResponse: {
            /** Run Id */
            run_id: string;
            /** Conversation Id */
            conversation_id: string;
            /** Request Id */
            request_id: string;
            /** Answer */
            answer: string;
            /** Answer Mode */
            answer_mode: string;
            /** Grounded */
            grounded: boolean;
            /** Degraded */
            degraded: boolean;
            /** Citations */
            citations: components["schemas"]["CitationResponse"][];
            /** Steps */
            steps: {
                [key: string]: unknown;
            }[];
            /** Duration Ms */
            duration_ms: number;
            /** Timings */
            timings?: {
                [key: string]: number;
            };
            /** Suggestions */
            suggestions?: string[];
            /** Resources */
            resources?: components["schemas"]["ResumeResource"][];
            /**
             * Cancelled
             * @default false
             */
            cancelled: boolean;
        };
        /**
         * AgentMessageRequest
         * @description 发送给 Agent 的问题和知识库过滤范围。
         */
        AgentMessageRequest: {
            /** Question */
            question: string;
            filters?: components["schemas"]["KnowledgeFilters"];
        };
        /** Body_replace_resume_api_v1_resume_put */
        Body_replace_resume_api_v1_resume_put: {
            /**
             * File
             * @description 新的 PDF 简历。
             */
            file: string;
            /** Title */
            title: string;
            /** Version */
            version: string;
        };
        /** Body_upload_document_api_v1_documents_post */
        Body_upload_document_api_v1_documents_post: {
            /**
             * File
             * @description 需要导入的 PDF、Markdown、TXT 或 DOCX 文件。
             */
            file: string;
        };
        /**
         * CareerMaterialSection
         * @description 一类岗位定制材料及其可信引用。
         */
        CareerMaterialSection: {
            /** Title */
            title: string;
            /** Content */
            content: string;
            /** Evidence */
            evidence?: components["schemas"]["CitationResponse"][];
        };
        /**
         * CareerMaterialsResponse
         * @description 围绕当前会话岗位生成的完整求职材料包。
         */
        CareerMaterialsResponse: {
            /** Analysis Id */
            analysis_id: string;
            /** Company Name */
            company_name: string | null;
            /** Job Title */
            job_title: string;
            /** Profile Version */
            profile_version: number | null;
            /** Score */
            score: number;
            /** Completeness */
            completeness: number;
            /** Feasibility */
            feasibility: number;
            /** Sections */
            sections: components["schemas"]["CareerMaterialSection"][];
        };
        /**
         * ChatRequest
         * @description 单次知识问答或闲聊请求。
         */
        ChatRequest: {
            /**
             * Question
             * @description 用户当前问题。
             */
            question: string;
            /**
             * Mode
             * @description 知识库模式强制检索；闲聊模式不生成知识库引用。
             * @default knowledge_base
             * @enum {string}
             */
            mode: "knowledge_base" | "casual";
            /** History */
            history?: components["schemas"]["HistoryMessage"][];
            filters?: components["schemas"]["KnowledgeFilters"];
        };
        /**
         * ChatResponse
         * @description 问答结果、回答模式、依据状态和引用列表。
         */
        ChatResponse: {
            /** Answer */
            answer: string;
            /**
             * Answer Mode
             * @enum {string}
             */
            answer_mode: "knowledge_base" | "casual";
            /** Grounded */
            grounded: boolean;
            /** Rewritten Query */
            rewritten_query: string;
            /** Citations */
            citations: components["schemas"]["CitationResponse"][];
            /** Retrieved Count */
            retrieved_count: number;
            /** Request Id */
            request_id: string;
        };
        /**
         * CitationResponse
         * @description 可核查到权威切片正文的单条引用。
         */
        CitationResponse: {
            /** Reference Number */
            reference_number: number;
            /** Chunk Id */
            chunk_id: string;
            /** Document Id */
            document_id: string;
            /** Filename */
            filename: string;
            /** Quote */
            quote: string;
            /** Page Number */
            page_number: number | null;
            /** Heading */
            heading: string | null;
            /** Index Version */
            index_version: number;
        };
        /**
         * ConversationListResponse
         * @description 管理员可见的会话分页结果。
         */
        ConversationListResponse: {
            /** Items */
            items: components["schemas"]["ConversationSummaryResponse"][];
            /** Offset */
            offset: number;
            /** Limit */
            limit: number;
        };
        /**
         * ConversationResponse
         * @description 会话元数据及其最近消息。
         */
        ConversationResponse: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Active Jd Analysis Id */
            active_jd_analysis_id?: string | null;
            /** Candidate Profile Version */
            candidate_profile_version?: number | null;
            /** Career Context Updated At */
            career_context_updated_at?: string | null;
            /** Messages */
            messages: components["schemas"]["MessageResponse"][];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * ConversationSummaryResponse
         * @description 会话列表中的轻量摘要，不重复返回全部消息。
         */
        ConversationSummaryResponse: {
            /** Id */
            id: string;
            /** Title */
            title: string;
            /** Active Jd Analysis Id */
            active_jd_analysis_id?: string | null;
            /** Candidate Profile Version */
            candidate_profile_version?: number | null;
            /** Career Context Updated At */
            career_context_updated_at?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * CreateConversationRequest
         * @description 创建会话时可选的显示标题。
         */
        CreateConversationRequest: {
            /**
             * Title
             * @default 新会话
             */
            title: string;
        };
        /**
         * DocumentAcceptedResponse
         * @description 文档操作成功进入后台队列后的响应。
         */
        DocumentAcceptedResponse: {
            document: components["schemas"]["DocumentResponse"];
            job: components["schemas"]["JobResponse"];
        };
        /**
         * DocumentListResponse
         * @description 分页文档列表。
         */
        DocumentListResponse: {
            /** Items */
            items: components["schemas"]["DocumentResponse"][];
            /** Offset */
            offset: number;
            /** Limit */
            limit: number;
        };
        /**
         * DocumentResponse
         * @description 对外展示的文档状态和活动索引信息。
         */
        DocumentResponse: {
            /** Id */
            id: string;
            /** Filename */
            filename: string;
            /** File Type */
            file_type: string;
            /** Status */
            status: string;
            /** Size Bytes */
            size_bytes: number;
            /** Chunk Count */
            chunk_count: number;
            /** Active Index Version */
            active_index_version: number;
            /**
             * Visibility
             * @enum {string}
             */
            visibility: "public" | "private";
            /** Error Message */
            error_message: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * DocumentVisibilityRequest
         * @description 修改文档访客可见范围的请求。
         */
        DocumentVisibilityRequest: {
            /**
             * Visibility
             * @description 文档公开范围。
             * @enum {string}
             */
            visibility: "public" | "private";
        };
        /**
         * ErrorDetail
         * @description 稳定错误代码和可直接展示的中文消息。
         */
        ErrorDetail: {
            /**
             * Code
             * @description 供程序判断错误类型的稳定代码。
             * @example document_not_found
             */
            code: string;
            /**
             * Message
             * @description 适合向用户展示的错误消息。
             * @example 文档不存在
             */
            message: string;
        };
        /**
         * ErrorResponse
         * @description 所有业务异常采用的统一外层结构。
         * @example {
         *       "error": {
         *         "code": "document_not_found",
         *         "message": "文档不存在"
         *       }
         *     }
         */
        ErrorResponse: {
            error: components["schemas"]["ErrorDetail"];
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * HealthResponse
         * @description 应用存活检查响应。
         */
        HealthResponse: {
            /**
             * Status
             * @constant
             */
            status: "ok";
            /** Service */
            service: string;
            /** Version */
            version: string;
        };
        /**
         * HistoryMessage
         * @description 用于查询改写的有限对话历史。
         */
        HistoryMessage: {
            /**
             * Role
             * @enum {string}
             */
            role: "user" | "assistant";
            /** Content */
            content: string;
        };
        /**
         * JdAnalysisRequest
         * @description 访客粘贴的岗位描述。
         */
        JdAnalysisRequest: {
            /** Jd Text */
            jd_text: string;
            /** Conversation Id */
            conversation_id?: string | null;
        };
        /**
         * JdAnalysisResponse
         * @description 完整且可持久化的岗位匹配报告。
         */
        JdAnalysisResponse: {
            /** Id */
            id: string;
            /** Request Id */
            request_id: string;
            /** Status */
            status: string;
            /** Company Name */
            company_name: string | null;
            /** Job Title */
            job_title: string | null;
            /** Score */
            score: number | null;
            /** Completeness */
            completeness: number | null;
            /** Verified Fit */
            verified_fit: number | null;
            /** Feasibility */
            feasibility: number | null;
            /** Requirements */
            requirements?: components["schemas"]["JdRequirement"][];
            /** Matches */
            matches?: components["schemas"]["JdRequirementMatch"][];
            /** Duration Ms */
            duration_ms: number | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * JdCancellationResponse
         * @description 服务端接受取消请求后的响应。
         */
        JdCancellationResponse: {
            /** Request Id */
            request_id: string;
            /**
             * Status
             * @default cancellation_requested
             */
            status: string;
        };
        /**
         * JdEvidence
         * @description 来自公开知识库且通过活动版本校验的证据。
         */
        JdEvidence: {
            /** Chunk Id */
            chunk_id: string;
            /** Document Id */
            document_id: string;
            /** Filename */
            filename: string;
            /** Quote */
            quote: string;
            /** Page Number */
            page_number?: number | null;
            /** Heading */
            heading?: string | null;
            /** Index Version */
            index_version: number;
            /** Score */
            score: number;
            /** Source Type */
            source_type: string;
            /** Source Quality */
            source_quality: number;
        };
        /**
         * JdRequirement
         * @description 从 JD 中提取的一项可验证要求。
         */
        JdRequirement: {
            /** Id */
            id: string;
            /** Requirement */
            requirement: string;
            /** Category */
            category: string;
            /**
             * Importance
             * @enum {string}
             */
            importance: "required" | "preferred";
            /** Weight */
            weight: number;
            /** Keywords */
            keywords?: string[];
            /** Requirement Type */
            requirement_type: string;
        };
        /**
         * JdRequirementMatch
         * @description 单项岗位要求的匹配结论。
         */
        JdRequirementMatch: {
            /** Requirement Id */
            requirement_id: string;
            /** Requirement */
            requirement: string;
            /** Category */
            category: string;
            /** Requirement Type */
            requirement_type: string;
            /**
             * Importance
             * @enum {string}
             */
            importance: "required" | "preferred";
            /** Weight */
            weight: number;
            /**
             * Level
             * @enum {string}
             */
            level: "strong_match" | "partial_match" | "missing" | "unverified" | "conflict";
            /** Reason */
            reason: string;
            /** Awarded Score */
            awarded_score: number;
            /** Max Score */
            max_score: number;
            /** Evidence */
            evidence?: components["schemas"]["JdEvidence"][];
        };
        /**
         * JobListResponse
         * @description 管理端任务中心使用的分页任务列表。
         */
        JobListResponse: {
            /** Items */
            items: components["schemas"]["JobResponse"][];
            /** Offset */
            offset: number;
            /** Limit */
            limit: number;
        };
        /**
         * JobResponse
         * @description 文档处理任务的当前状态。
         */
        JobResponse: {
            /** Id */
            id: string;
            /** Document Id */
            document_id: string | null;
            /** Operation */
            operation: string;
            /** Target Index Version */
            target_index_version: number;
            /** Status */
            status: string;
            /** Progress */
            progress: number;
            /** Attempts */
            attempts: number;
            /** Error Message */
            error_message: string | null;
            /** Started At */
            started_at: string | null;
            /** Finished At */
            finished_at: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * KnowledgeFilters
         * @description 限制知识检索范围的可选元数据。
         */
        KnowledgeFilters: {
            /** Document Ids */
            document_ids?: string[];
            /** Filenames */
            filenames?: string[];
        };
        /**
         * MessageResponse
         * @description 持久化的单条会话消息。
         */
        MessageResponse: {
            /** Id */
            id: string;
            /** Role */
            role: string;
            /** Content */
            content: string;
            /** Citations Json */
            citations_json: {
                [key: string]: unknown;
            }[] | null;
            /** Suggestions Json */
            suggestions_json: string[] | null;
            /** Resources Json */
            resources_json: components["schemas"]["ResumeResource"][] | null;
            /** Artifacts Json */
            artifacts_json: {
                [key: string]: unknown;
            }[] | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /**
         * ReadinessResponse
         * @description 应用依赖就绪检查响应。
         */
        ReadinessResponse: {
            /**
             * Status
             * @constant
             */
            status: "ready";
            /**
             * Database
             * @constant
             */
            database: "ok";
            /**
             * Document Store
             * @constant
             */
            document_store: "ok";
            /**
             * Vector Store
             * @constant
             */
            vector_store: "ok";
        };
        /**
         * ResumeResource
         * @description 向访客公开的当前简历信息，不包含服务器真实路径。
         */
        ResumeResource: {
            /**
             * Type
             * @default resume
             * @constant
             */
            type: "resume";
            /** Title */
            title: string;
            /** Description */
            description: string;
            /** Filename */
            filename: string;
            /** Version */
            version: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Size Bytes */
            size_bytes: number;
            /**
             * Media Type
             * @default application/pdf
             * @constant
             */
            media_type: "application/pdf";
            /** Download Url */
            download_url: string;
            /** Preview Url */
            preview_url: string;
        };
        /**
         * SpeechCancellationResponse
         * @description 服务端已接收指定语音任务的取消请求。
         */
        SpeechCancellationResponse: {
            /** Request Id */
            request_id: string;
            /**
             * Status
             * @default cancellation_requested
             */
            status: string;
        };
        /**
         * SpeechSynthesisRequest
         * @description 请求将一段已经完成的回答转换为语音。
         */
        SpeechSynthesisRequest: {
            /**
             * Text
             * @description 需要朗读的回答正文。
             */
            text: string;
            /**
             * Speech Rate
             * @description 播放语速；1.0 表示正常速度。
             * @default 1
             */
            speech_rate: number;
            /**
             * Character Id
             * @description 当前负责朗读的精灵角色。
             * @default nova
             * @enum {string}
             */
            character_id: "nova" | "byte" | "momo";
        };
        /**
         * SuggestionResponse
         * @description 前端可直接展示的推荐问题集合。
         */
        SuggestionResponse: {
            /** Suggestions */
            suggestions: string[];
            /**
             * Source
             * @enum {string}
             */
            source: "cache" | "generated" | "fallback" | "stored";
            /** Generated At */
            generated_at?: string | null;
        };
        /**
         * TtsVoiceProfileListResponse
         * @description 管理端读取的全部角色音色。
         */
        TtsVoiceProfileListResponse: {
            /** Items */
            items: components["schemas"]["TtsVoiceProfileResponse"][];
        };
        /**
         * TtsVoiceProfileResponse
         * @description 访客端和管理端可读取的角色音色配置。
         */
        TtsVoiceProfileResponse: {
            /**
             * Character Id
             * @enum {string}
             */
            character_id: "nova" | "byte" | "momo";
            /** Display Name */
            display_name: string;
            /** Model */
            model: string;
            /** Voice */
            voice: string;
            /** Enabled */
            enabled: boolean;
            /** Auto Speak */
            auto_speak: boolean;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * TtsVoiceProfileUpdate
         * @description 管理员允许修改的 CosyVoice 参数。
         */
        TtsVoiceProfileUpdate: {
            /** Model */
            model: string;
            /** Voice */
            voice: string;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
            /**
             * Auto Speak
             * @default true
             */
            auto_speak: boolean;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 应用名称、版本和存活状态。 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthResponse"];
                };
            };
        };
    };
    readiness_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 数据库、文档目录和向量库的就绪状态。 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReadinessResponse"];
                };
            };
        };
    };
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AdminLoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminTokenResponse"];
                };
            };
            /** @description 管理员密码错误。 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_current_admin_api_v1_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminProfileResponse"];
                };
            };
            /** @description 登录状态无效或已过期。 */
            401: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_documents_api_v1_documents_get: {
        parameters: {
            query?: {
                /** @description 从第几条文档开始读取。 */
                offset?: number;
                /** @description 本次最多返回多少条文档。 */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description 文档列表及本次分页参数。 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_document_api_v1_documents_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_document_api_v1_documents_post"];
            };
        };
        responses: {
            /** @description 已保存的文档和等待执行的后台任务。 */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentAcceptedResponse"];
                };
            };
            /** @description 文件为空、格式不支持或文件名不合法。 */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 相同内容的文档已经存在。 */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 文件超过配置的大小限制。 */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_document_api_v1_documents__document_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 上传文档时返回的文档 ID。 */
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentResponse"];
                };
            };
            /** @description 文档不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_document_api_v1_documents__document_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 需要删除的文档 ID。 */
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentAcceptedResponse"];
                };
            };
            /** @description 文档不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 该文档已有任务正在执行。 */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_document_visibility_api_v1_documents__document_id__visibility_patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 需要修改公开范围的文档 ID。 */
                document_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DocumentVisibilityRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentResponse"];
                };
            };
            /** @description 文档不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reindex_document_api_v1_documents__document_id__reindex_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 需要重新索引的文档 ID。 */
                document_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentAcceptedResponse"];
                };
            };
            /** @description 文档不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 已有任务执行中或原始文件丢失。 */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_ingestion_jobs_api_v1_ingestion_jobs_get: {
        parameters: {
            query?: {
                /** @description 可选任务状态。 */
                status?: string | null;
                offset?: number;
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_ingestion_job_api_v1_ingestion_jobs__job_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 文档操作返回的任务 ID。 */
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobResponse"];
                };
            };
            /** @description 任务不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    query_knowledge_api_v1_chat_query_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChatRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChatResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 模型密钥未配置或模型服务不可用。 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    list_conversations_api_v1_conversations_get: {
        parameters: {
            query?: {
                /** @description 从第几条会话开始读取。 */
                offset?: number;
                /** @description 最多返回多少条会话。 */
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_conversation_api_v1_conversations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CreateConversationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_conversation_api_v1_conversations__conversation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 会话 ID。 */
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationResponse"];
                };
            };
            /** @description 会话不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_conversation_api_v1_conversations__conversation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 需要删除的会话 ID。 */
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description 会话不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    send_agent_message_api_v1_conversations__conversation_id__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 会话 ID。 */
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AgentMessageRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentExecutionResponse"];
                };
            };
            /** @description 会话不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description 相同请求 ID 已执行。 */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stream_agent_message_api_v1_conversations__conversation_id__messages_stream_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 会话 ID。 */
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AgentMessageRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description 会话不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_agent_run_api_v1_conversations__conversation_id__runs__request_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 运行所属的会话 ID。 */
                conversation_id: string;
                /** @description 流式请求使用的 X-Request-ID。 */
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentCancellationResponse"];
                };
            };
            /** @description 会话或活动运行不存在。 */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    analyze_jd_api_v1_jd_analyses_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["JdAnalysisRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JdAnalysisResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_jd_analysis_api_v1_jd_analyses__analysis_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description JD 分析 ID。 */
                analysis_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JdAnalysisResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stream_jd_analysis_api_v1_jd_analyses_stream_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["JdAnalysisRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_jd_analysis_api_v1_jd_analyses_runs__request_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 前端提交的请求 ID。 */
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JdCancellationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_career_materials_api_v1_career_conversations__conversation_id__materials_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 已绑定 JD 的会话 ID。 */
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CareerMaterialsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_career_report_api_v1_career_conversations__conversation_id__report_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 已绑定 JD 的会话 ID。 */
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_empty_suggestions_api_v1_suggestions_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SuggestionResponse"];
                };
            };
        };
    };
    stream_speech_api_v1_tts_stream_post: {
        parameters: {
            query?: never;
            header: {
                "X-Request-ID": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SpeechSynthesisRequest"];
            };
        };
        responses: {
            /** @description MP3 音频流。 */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "audio/mpeg": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description 尚未配置 DashScope。 */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    get_voice_profile_api_v1_tts_profiles__character_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 精灵角色 ID。 */
                character_id: "nova" | "byte" | "momo";
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TtsVoiceProfileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_voice_profile_api_v1_tts_profiles__character_id__put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 精灵角色 ID。 */
                character_id: "nova" | "byte" | "momo";
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TtsVoiceProfileUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TtsVoiceProfileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_voice_profiles_api_v1_tts_profiles_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TtsVoiceProfileListResponse"];
                };
            };
        };
    };
    cancel_speech_api_v1_tts_runs__request_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                /** @description 语音请求使用的 X-Request-ID。 */
                request_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SpeechCancellationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_resume_info_api_v1_resume_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResumeResource"];
                };
            };
        };
    };
    replace_resume_api_v1_resume_put: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_replace_resume_api_v1_resume_put"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ResumeResource"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_resume_api_v1_resume_download_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
    preview_resume_api_v1_resume_preview_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
        };
    };
}
