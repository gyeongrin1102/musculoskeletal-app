-- 근로자 설문 화면(로그인하지 않은 상태)에서 중복 제출 여부만 확인하는 함수
-- survey_results 에 RLS 가 걸려 있어도 응답 내용은 열어 주지 않고, 있음/없음만 돌려줍니다.
-- Supabase 대시보드 > SQL Editor 에 붙여 넣고 Run 하세요. (한 번만 실행)

create or replace function public.survey_already_submitted(
    p_name text,
    p_department text,
    p_gender text,
    p_year int
)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
    select exists (
        select 1
        from public.survey_results
        where name = p_name
          and department = p_department
          and (coalesce(gender, '') = '' or p_gender = '' or gender = p_gender)
          and created_at >= make_date(p_year, 1, 1)
          and created_at <  make_date(p_year + 1, 1, 1)
    );
$$;

grant execute on function public.survey_already_submitted(text, text, text, int)
    to anon, authenticated;
