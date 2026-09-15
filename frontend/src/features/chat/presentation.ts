/** 判断回答应使用的视觉呈现方式，不参与后端意图路由。 */

const PROFILE_SUBJECT_PATTERN = /zyw|曾有为/i;
const PROFILE_INTENT_PATTERN = /介绍|简介|认识|了解|说说|讲讲|是谁|做什么/i;
const PROFILE_FOCUSED_TOPIC_PATTERN =
  /某个|这个|哪个|项目|技术|技能|经历|工作|公司|学历|知识库|agent|rag/i;

export function isProfileIntroductionQuestion(question: string): boolean {
  /** 只有宽泛的个人介绍使用人物卡，具体问题继续显示为普通回答。 */
  const normalized = question.trim().replaceAll(/\s+/g, " ");
  return (
    PROFILE_SUBJECT_PATTERN.test(normalized) &&
    PROFILE_INTENT_PATTERN.test(normalized) &&
    !PROFILE_FOCUSED_TOPIC_PATTERN.test(normalized)
  );
}

export function profileAnswerContent(content: string): string {
  /** 人物卡已经自带标题，移除模型可能重复输出的同名 Markdown 标题。 */
  return content.replace(/^\s*#{0,3}\s*认识一下\s*ZYW\s*/i, "").trimStart();
}
