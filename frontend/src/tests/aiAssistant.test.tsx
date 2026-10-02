import {describe,expect,it,vi} from 'vitest';
import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {AiAssistantPage} from '../pages/AiAssistantPage';
import {AiProvider} from '../contexts/AiContext';

const {aiChat}=vi.hoisted(()=>({aiChat:vi.fn()}));
vi.mock('../lib/api',()=>({qh:{aiChat}}}));

describe('AI assistant UI',()=>{
  it('renders the research assistant and sends an example prompt through the shared API',async()=>{
    aiChat.mockResolvedValue({reply:'The hybrid workflow combines classical and quantum components.'});
    const user=userEvent.setup();
    render(<AiProvider><AiAssistantPage/></AiProvider>);

    expect(screen.getByText('EntangleX AI Assistant')).toBeInTheDocument();
    await user.click(screen.getByRole('button',{name:'What is EntangleX Q-Health?'}));

    expect(aiChat).toHaveBeenCalledWith({
      message:'What is EntangleX Q-Health?',
      conversation:[],
    });
    expect(await screen.findByText(/The hybrid workflow combines/)).toBeInTheDocument();
  });
});
